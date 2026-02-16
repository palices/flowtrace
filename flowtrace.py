import argparse
import inspect
import json
import threading
import runpy
import sys
import time
import sysconfig
import tracemalloc
from pathlib import Path


class TraceradoProfiler:
    def __init__(self, script_path, output_path, script_args=None):
        self.script_path = Path(script_path).resolve()
        self.output_path = Path(output_path)
        # argumentos que se pasaran al script perfilado (por ejemplo: -- foo 1 bar)
        self.script_args = list(script_args or [])
        if self.script_args and self.script_args[0] == "--":
            self.script_args = self.script_args[1:]
        self.records = []
        self._inflight = {}
        self._stack = []
        self._instance_roots = {}
        self._next_id = 1
        self._root_entry = None
        self._root_dir = self.script_path.parent
        # rutas a ignorar: stdlib y site-packages
        self._ignore_prefixes = []
        for key in ("stdlib", "platstdlib", "purelib", "platlib"):
            p = sysconfig.get_paths().get(key)
            if p:
                self._ignore_prefixes.append(Path(p).resolve())
        for p in (sys.prefix, sys.base_prefix, sys.exec_prefix):
            try:
                self._ignore_prefixes.append(Path(p).resolve())
            except Exception:
                pass
        self._tracemalloc_enabled = False
        self._write_lock = threading.Lock()
        self._flush_interval = 0.2
        self._last_flush = -1e9  # fuerza un primer flush inmediato
        self._stop_flush = threading.Event()
        self._flush_thread = None
        self._last_seen_callable = None

    def _memory_snapshot(self):
        snapshot = {}
        try:
            import psutil  # type: ignore

            proc = psutil.Process()
            with proc.oneshot():
                mem = proc.memory_info()
                snapshot["rss_bytes"] = mem.rss
                snapshot["vms_bytes"] = mem.vms
        except Exception:
            # psutil no disponible o falló; continuamos con tracemalloc si está activo
            pass
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            snapshot["py_tracemalloc_current"] = current
            snapshot["py_tracemalloc_peak"] = peak
        return snapshot

    def _serialize(self, value, depth=0, max_depth=3):
        if depth >= max_depth:
            return repr(value)
        if isinstance(value, dict):
            return {
                str(key): self._serialize(val, depth + 1, max_depth)
                for key, val in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [self._serialize(val, depth + 1, max_depth) for val in value]
        if hasattr(value, "__dict__"):
            return self._serialize(value.__dict__, depth + 1, max_depth)
        try:
            json.dumps(value)
            return value
        except TypeError:
            return repr(value)

    def _capture_inputs(self, frame):
        try:
            args = inspect.getargvalues(frame)
        except Exception:
            return {}

        values = {name: frame.f_locals.get(name) for name in args.args}
        if args.varargs:
            values[args.varargs] = frame.f_locals.get(args.varargs)
        if args.keywords:
            values[args.keywords] = frame.f_locals.get(args.keywords)
        values.pop("self", None)
        values.pop("cls", None)
        return {key: self._serialize(val) for key, val in values.items()}

    def _get_class_name(self, frame):
        if "self" in frame.f_locals:
            return type(frame.f_locals["self"]).__name__
        if "cls" in frame.f_locals and inspect.isclass(frame.f_locals["cls"]):
            return frame.f_locals["cls"].__name__
        return None

    def _should_trace(self, frame):
        filename_str = frame.f_code.co_filename
        module_name = frame.f_globals.get("__name__", "")
        # descartar frames internos/builtins/frozen
        if filename_str.startswith("<"):
            return False
        if module_name.startswith(("importlib", "encodings", "zipimport")):
            return False
        try:
            filename = Path(filename_str).resolve()
        except Exception:
            return False
        if filename == Path(__file__).resolve():
            return False
        # ignorar stdlib / site-packages
        for prefix in self._ignore_prefixes:
            try:
                filename.relative_to(prefix)
                return False
            except ValueError:
                continue
        # trazar cualquier archivo dentro del directorio raíz del script
        try:
            filename.relative_to(self._root_dir)
            return True
        except ValueError:
            return False

    def _is_class_constructor_call(self, frame):
        if frame.f_globals.get("__name__") != "__main__":
            return False
        name = frame.f_code.co_name
        obj = frame.f_globals.get(name)
        return inspect.isclass(obj)

    def _is_class_definition(self, frame):
        if "__module__" not in frame.f_locals or "__qualname__" not in frame.f_locals:
            return False
        return frame.f_code.co_name == frame.f_locals.get("__qualname__")

    def _profile(self, frame, event, arg):
        if not self._should_trace(frame):
            return

        if frame.f_code.co_name == "<module>":
            return
        if self._is_class_definition(frame):
            return
        if self._is_class_constructor_call(frame):
            return

        frame_id = id(frame)
        if event == "call":
            class_name = self._get_class_name(frame)
            instance_id = None
            if "self" in frame.f_locals:
                instance_id = id(frame.f_locals["self"])
            if frame.f_code.co_name == "__init__" and instance_id is not None:
                if instance_id not in self._instance_roots:
                    instance_entry = {
                        "id": self._next_id,
                        "callable": "__instance__",
                        "module": frame.f_globals.get("__name__", ""),
                        "called": class_name if class_name else frame.f_code.co_name,
                        "instance_id": instance_id,
                        "inputs": self._capture_inputs(frame),
                        "output": None,
                        "error": None,
                        "duration_ms": None,
                        "calls": [],
                    }
                    self._next_id += 1
                    root_calls = (
                        self._root_entry["calls"]
                        if self._root_entry is not None
                        else self.records
                    )
                    root_calls.append(instance_entry)
                    self._instance_roots[instance_id] = instance_entry

            entry = {
                "id": self._next_id,
                "callable": frame.f_code.co_name,
                "module": frame.f_globals.get("__name__", ""),
                "called": class_name if class_name else frame.f_code.co_name,
                "caller": None,
                "instance_id": instance_id,
                "inputs": self._capture_inputs(frame),
                "calls": [],
            }
            self._next_id += 1
            self._inflight[frame_id] = (entry, time.time())
            self._last_seen_callable = entry["callable"]
            if self._stack:
                parent = self._stack[-1]
                entry["caller"] = f"{parent.get('called')}::{parent.get('callable')}"
            if instance_id is not None and instance_id in self._instance_roots:
                parent = self._stack[-1] if self._stack and self._stack[-1].get(
                    "instance_id"
                ) == instance_id else self._instance_roots[instance_id]
                parent["calls"].append(entry)
            elif self._stack:
                self._stack[-1]["calls"].append(entry)
            else:
                self.records.append(entry)
            self._stack.append(entry)
            entry["memory_before"] = self._memory_snapshot()
            self._maybe_flush(force=True, current=entry["callable"], log=True)
            return

        if frame_id not in self._inflight:
            return

        entry, started = self._inflight[frame_id]
        if event == "return":
            entry["inputs_after"] = self._capture_inputs(frame)
            if entry.get("error") is None:
                entry["output"] = self._serialize(arg)
                entry["error"] = None
            entry["duration_ms"] = round((time.time() - started) * 1000, 3)
            entry["memory_after"] = self._memory_snapshot()
            self._inflight.pop(frame_id, None)
            if self._stack and self._stack[-1] is entry:
                self._stack.pop()
            self._maybe_flush(force=True, current=entry["callable"], log=True)
        elif event == "exception":
            exc_type, exc_value, _ = arg
            entry["inputs_after"] = self._capture_inputs(frame)
            entry["output"] = None
            entry["error"] = repr(exc_value if exc_value else exc_type)
            entry["duration_ms"] = round((time.time() - started) * 1000, 3)
            entry["memory_after"] = self._memory_snapshot()
            self._inflight.pop(frame_id, None)
            if self._stack and self._stack[-1] is entry:
                self._stack.pop()
            self._maybe_flush(force=True, current=entry["callable"], log=True)

    def run(self):
        script_name = self.script_path.name
        self._root_entry = {
            "id": 0,
            "callable": script_name,
            "module": "__main__",
            "called": script_name,
            "inputs": {},
            "output": None,
            "error": None,
            "duration_ms": None,
            "calls": [],
        }
        self.records = [self._root_entry]
        self._stack = [self._root_entry]
        tracemalloc.start(10)
        self._tracemalloc_enabled = True
        self._root_entry["memory_before"] = self._memory_snapshot()
        self._maybe_flush(force=True, current=self._root_entry.get("callable"), log=True)  # snapshot inicial
        sys.setprofile(self._profile)
        old_argv = sys.argv
        # emula la ejecucion normal del script, permitiendo argumentos personalizados
        sys.argv = [str(self.script_path)] + self.script_args
        exc_raised: BaseException | None = None
        # lanzar thread que flushea cada _flush_interval
        self._stop_flush.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        try:
            runpy.run_path(str(self.script_path), run_name="__main__")
        except BaseException as exc:  # capturamos para reflejar error en la raiz
            exc_raised = exc
            self._root_entry["error"] = repr(exc)
            self._root_entry["output"] = None
            # marca como error cualquier frame inflight (p.ej. validate_config)
            now = time.time()
            for entry, started in list(self._inflight.values()):
                entry["output"] = None
                entry["error"] = repr(exc)
                entry["duration_ms"] = round((now - started) * 1000, 3)
                entry["memory_after"] = self._memory_snapshot()
            self._propagate_error(self._root_entry, repr(exc))
        finally:
            sys.argv = old_argv
            sys.setprofile(None)
            self._root_entry["memory_after"] = self._memory_snapshot()
            if self._tracemalloc_enabled:
                tracemalloc.stop()
            self._prune_calls(self._root_entry)
            self._maybe_flush(force=True)
            self._stop_flush.set()
            if self._flush_thread:
                self._flush_thread.join(timeout=1)
            print()
        if exc_raised:
            raise exc_raised

    def _prune_calls(self, node):
        pruned = []
        for child in node.get("calls", []):
            self._prune_calls(child)
            if self._is_class_definition_node(child):
                pruned.extend(child.get("calls", []))
                continue
            if child.get("callable") == "__instance__" and not child.get("calls"):
                continue
            if (
                child.get("callable") == "__init__"
                and not child.get("calls")
                and child.get("output") is None
                and child.get("error") is None
            ):
                continue
            pruned.append(child)
        node["calls"] = pruned

    def _propagate_error(self, node, exc_repr):
        if node.get("output") is None and node.get("error") is None:
            node["error"] = exc_repr
        for child in node.get("calls", []):
            self._propagate_error(child, exc_repr)

    def _write_output(self, payload):
        with open(self.output_path, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
            f.flush()

    def _maybe_flush(self, force=False, current=None, log=False):
        now = time.time()
        if not force and now - self._last_flush < self._flush_interval:
            return
        with self._write_lock:
            snapshot = json.dumps(self.records, indent=2, ensure_ascii=True)
            current_call = (
                current
                or (f"{self._stack[-1].get('module','')}::{self._stack[-1].get('callable','')}" if self._stack else None)
                or self._last_seen_callable
                or self._root_entry.get("callable", "")
            )
        self._last_flush = now
        if log:
            sys.stderr.write(
                f"[FlowTrace] Guardando snapshot (callable={current_call}) en {self.output_path}\n"
            )
            sys.stderr.flush()
        self._write_output(snapshot)

    def _flush_loop(self):
        while not self._stop_flush.is_set():
            try:
                self._maybe_flush(log=False)
            except Exception:
                pass
            time.sleep(self._flush_interval)

    def _is_class_definition_node(self, node):
        # class definitions ya se excluyeron en _is_class_definition del tracer
        return False


def _parse_args():
    parser = argparse.ArgumentParser(description="Tracerado JSON profiler")
    parser.add_argument(
        "-s",
        "--script",
        required=True,
        help="Ruta del script a ejecutar",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="flowtrace.json",
        help="Ruta del JSON de salida",
    )
    args, unknown = parser.parse_known_args()
    # cualquier argumento no reconocido se pasa al script perfilado
    args.script_args = list(unknown)
    if args.script_args and args.script_args[0] == "--":
        args.script_args = args.script_args[1:]
    return args


def main():
    args = _parse_args()
    profiler = TraceradoProfiler(args.script, args.output, args.script_args)
    profiler.run()


if __name__ == "__main__":
    main()
