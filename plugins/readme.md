# Pytraceflow Plugin for PyCharm

## What it does
- Adds a gutter icon on Python breakpoints; clicking shows a popup with trace blocks from `pytraceflow` JSON runs.
- Detects the callable at the breakpoint line and highlights matching trace nodes.
- Popup includes a call tree, detail pane (summary, memory in MB, formatted inputs/outputs/errors), search filter by callable/called, refresh, "Generate Pytraceflow json" runner, and a help dialog with CLI options and examples.
- Command field is editable; generation runs exactly what you type. Default: `python pytraceflow.py -s <script> <args>`.

## Install
1. Install in PyCharm: Settings -> Plugins -> gear -> Install Plugin from Disk -> select the ZIP in plugins folder.
2. Restart the IDE.

## Usage
- Place a breakpoint on the first non-whitespace element of a Python line; the yellow diamond icon appears.
- Click the icon: popup opens with a tree on the left (30%) and details on the right (70%).
- Search: type text to filter by callable/called.
- Generate execution flow JSON: edit Command if needed -> click "Generate Pytraceflow json". While running, the button shows "Generating...". JSON load priority: path in command (if any), then `ptf.json`, then `pytraceflow.json`.
- Help ("?"): shows CLI options and usage examples.
- Calls list: displays each child callable with its duration.

## CLI options (from help)
- `-s/--script` (required): target script path.
- `-o/--output`: JSON output path (default `pft.json`).
- `--flush-interval`: seconds between flushes; <=0 disables the thread (default 1.0).
- `--flush-every-call`: flush on every event (slow; legacy).
- `--log-flushes`: log each flush to stderr.
- `--with-memory` / `--no-memory` / `--no-tracemalloc` / `--skip-inputs`.
- OTLP export: `--export-otlp-endpoint` URL, `--export-otlp-service` NAME, repeat `--export-otlp-header key=value`.
- Other args are forwarded to the profiled script.

## Usage examples
- Default fast: `python pytraceflow.py -s samples/basic/basic_sample.py -o pft.json`
- With memory: `python pytraceflow.py -s samples/basic/basic_sample.py --with-memory --flush-interval 2.0`
- Minimal overhead: `python pytraceflow.py -s samples/basic/basic_sample.py --flush-interval 0 --skip-inputs`
- Legacy per-call flush + logs: `python pytraceflow.py -s samples/basic/basic_sample.py --flush-every-call --log-flushes`
- Memory via psutil only: `python pytraceflow.py -s samples/basic/basic_sample.py --with-memory --no-tracemalloc`

## Notes
- Memory values in the detail pane are shown in MB.
- If no callable match is found, the tree is empty and the detail pane reports no matches.
- Editable command field is not auto-overwritten after edits.
