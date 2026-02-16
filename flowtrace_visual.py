import argparse
import html
import json
from pathlib import Path


def _escape(value):
    if value is None:
        return "null"
    if isinstance(value, (dict, list, tuple)):
        return html.escape(json.dumps(value, indent=2, ensure_ascii=True))
    return html.escape(str(value))


def _render_field(
    label, value, opened=False, extra_class="", icon_class="", raw_html=False, attrs=""
):
    content = value if raw_html else _escape(value)
    return (
        "<details class='field-block "
        + extra_class
        + "' "
        + attrs
        + " "
        + ("open" if opened else "")
        + ">"
        + "<summary class='field-label'>"
        + f"<span class='icon {icon_class}' aria-hidden='true'></span>"
        + f"{_escape(label)}</summary>"
        + (content if raw_html else f"<pre>{content}</pre>")
        + "</details>"
    )


def _group_calls(calls):
    grouped = {}
    ordered = []
    for call in calls:
        key = (call.get("module"), call.get("called"), call.get("callable"))
        if key not in grouped:
            grouped[key] = {"key": key, "calls": []}
            ordered.append(grouped[key])
        grouped[key]["calls"].append(call)
    return ordered


def _render_calls(calls, depth, node_id, node_title, path):
    total = len(calls)
    if not total:
        return ""
    body = ""
    for g_idx, group in enumerate(_group_calls(calls)):
        key = group["key"]
        label = f"{key[1]} :: {key[2]} (x{len(group['calls'])})"
        if len(group["calls"]) == 1:
            body += _render_node(group["calls"][0], depth + 1, path=f"{path}-g{g_idx}")
        else:
            body += (
                "<details class='group'>"
                + f"<summary class='group-title'>{_escape(label)}</summary>"
                + "<div class='group-body'>"
                + "".join(
                    _render_node(child, depth + 1, path=f"{path}-g{g_idx}-c{idx}")
                    for idx, child in enumerate(group["calls"])
                )
                + "</div></details>"
            )
    calls_id = f"calls-{node_id}" if node_id is not None else f"calls-{path}"
    field = _render_field(
        f"calls ({total})",
        "<div class='calls-preview' data-i18n='callsPreview'>Abrir llamadas</div>",
        opened=False,
        extra_class="calls-field",
        icon_class="icon-calls",
        raw_html=True,
        attrs="".join(
            [
                f"data-calls-id='{calls_id}' ",
                f"data-calls-title='{_escape(node_title)}' ",
                "data-i18n-label='calls' ",
                f"data-count='{total}' ",
                f"data-node-path='{_escape(path)}' ",
            ]
        ),
    )
    template = f"<template id='{calls_id}'>{body}</template>"
    return field + template


def _render_node(node, depth=0, path="r"):
    if node.get("callable") == "__instance__":
        title = node.get("called")
    else:
        title = node.get("callable")
    module = node.get("module")
    duration = node.get("duration_ms")
    error = node.get("error")
    caller = node.get("caller")
    mem_before = node.get("memory_before")
    mem_after = node.get("memory_after")
    inputs = node.get("inputs")
    inputs_after = node.get("inputs_after")
    output = node.get("output")
    calls = node.get("calls", [])
    node_id = node.get("id")
    dom_id = node_id if node_id is not None else path

    def _pick_mem(snapshot):
        if not isinstance(snapshot, dict):
            return None
        for key in ("rss_bytes", "py_tracemalloc_current", "vms_bytes", "py_tracemalloc_peak"):
            if key in snapshot and snapshot[key] is not None:
                return snapshot[key], key
        return None

    def _fmt_bytes(num):
        try:
            num = float(num)
        except Exception:
            return str(num)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if abs(num) < 1024.0 or unit == units[-1]:
                return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} TB"

    mem_label_map = {
        "rss_bytes": "rss",
        "vms_bytes": "vms",
        "py_tracemalloc_current": "py",
        "py_tracemalloc_peak": "py_peak",
    }

    def _format_mem(before, after):
        b = _pick_mem(before)
        a = _pick_mem(after)
        if not b and not a:
            return None
        label = mem_label_map.get((b or a)[1], "mem")
        if b and a:
            return f"{_fmt_bytes(b[0])}→{_fmt_bytes(a[0])} {label}"
        if a:
            return f"{_fmt_bytes(a[0])} {label}"
        return f"{_fmt_bytes(b[0])} {label}"

    mem_text = _format_mem(mem_before, mem_after)

    parts = [
        "<summary>",
        f"<span class='title'>{_escape(title)}</span>",
        "<span class='summary-meta'>",
        f"<span class='badge badge-module'>module: {_escape(module)}</span>",
        f"<span class='badge badge-duration'>duration_ms: {_escape(duration)}</span>",
        f"<span class='badge badge-error'>error: {_escape(error)}</span>",
        f"<span class='badge badge-caller'>caller: {_escape(caller)}</span>",
        (
            f"<span class='badge badge-memory'>mem: {_escape(mem_text)}</span>"
            if mem_text
            else ""
        ),
        "</span>",
        "</summary>",
    ]
    parts.append("<div class='content'>")
    inputs_class = "inputs-field"
    if not inputs:
        inputs_class += " inputs-empty"
    parts.append(
        _render_field(
            "inputs", inputs, opened=False, extra_class=inputs_class, icon_class="icon-in"
        )
    )
    if inputs_after is not None and inputs_after != inputs:
        parts.append(
            _render_field(
                "inputs_after",
                inputs_after,
                opened=False,
                icon_class="icon-in-after",
            )
        )
    output_class = "output-field"
    if output is None and not error:
        output_class += " output-empty"
    parts.append(
        _render_field(
            "output",
            output,
            opened=False,
            extra_class=output_class,
            icon_class="icon-out",
        )
    )
    if calls:
        parts.append(_render_calls(calls, depth, dom_id, title, path))
    parts.append("</div>")
    hue = (30 + depth * 38) % 360
    extra_cls = " python-internal" if str(node.get("callable", "")).startswith("<") else ""
    return (
        "<details class='node"
        + extra_cls
        + "' "
        + f"data-node-id='{_escape(dom_id)}' "
        + f"data-node-title='{_escape(title)}' "
        + f"style='--hue:"
        + str(hue)
        + "'>"
        + "".join(parts)
        + "</details>"
    )


def _render_html(data):
    root_nodes = data
    if isinstance(data, list):
        root_nodes = data
    elif isinstance(data, dict) and "calls" in data:
        root_nodes = [data]
    else:
        root_nodes = []

    tree = "".join(_render_node(node, path=f"r{idx}") for idx, node in enumerate(root_nodes))
    data_json = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FlowTrace</title>
  <style>
    :root {{
      --bg: #f6f2e8;
      --ink: #1f1a13;
      --muted: #6e6254;
      --card: #fff8ee;
      --accent: #c55b2a;
      --shadow: rgba(0,0,0,0.08);
    }}
    body.theme-dark {{
      --bg: #0f1117;
      --ink: #e8edf7;
      --muted: #9aa4b5;
      --card: #161b27;
      --accent: #7cc4ff;
      --shadow: rgba(0,0,0,0.25);
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 20%, #fff2d9, #f6f2e8);
      color: var(--ink);
      font-family: "Cormorant Garamond", "Georgia", serif;
    }}
    body.theme-dark {{
      background: radial-gradient(circle at 20% 20%, #1b2333, #0f1117);
    }}
    body.no-badges .summary-meta {{
      display: none;
    }}
    body.hide-badge-module .badge-module {{
      display: none;
    }}
    body.hide-badge-duration .badge-duration {{
      display: none;
    }}
    body.hide-badge-error .badge-error {{
      display: none;
    }}
    body.hide-badge-caller .badge-caller {{
      display: none;
    }}
    body.hide-badge-memory .badge-memory {{
      display: none;
    }}
    body.hide-python-internals .python-internal {{
      display: none;
    }}
    body.inputs-on-demand .inputs-empty {{
      display: none;
    }}
    body.output-on-demand .output-empty {{
      display: none;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 24px 8px;
      position: sticky;
      top: 0;
      z-index: 10;
      background: linear-gradient(180deg, #fff2d9 0%, #f6f2e8 100%);
      border-bottom: 1px solid #e2d8c6;
    }}
    body.theme-dark header {{
      background: linear-gradient(180deg, #1a2334 0%, #0f1117 100%);
      border-bottom: 1px solid #1f2635;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      padding: 8px 24px 14px;
      position: sticky;
      top: 66px;
      z-index: 9;
      background: #f6f2e8;
      border-bottom: 1px solid #e2d8c6;
    }}
    body.theme-dark .controls {{
      background: #0f1117;
      border-bottom: 1px solid #1f2635;
    }}
    .controls label {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
    }}
    .search-bar {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .search-input {{
      padding: 6px 10px;
      border: 1px solid #e2d8c6;
      border-radius: 8px;
      min-width: 240px;
      font-family: "IBM Plex Mono", "Courier New", monospace;
    }}
    .search-count {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
    }}
    h1 {{
      font-size: 28px;
      margin: 0;
      letter-spacing: 0.5px;
    }}
    button {{
      border: 1px solid var(--ink);
      background: var(--card);
      color: var(--ink);
      padding: 8px 14px;
      font-family: "IBM Plex Mono", "Courier New", monospace;
      cursor: pointer;
    }}
    body.theme-dark button {{
      border-color: #3d4b66;
    }}
    .lang-dropdown {{
      position: relative;
      display: inline-block;
    }}
    .lang-current {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--ink);
      background: var(--card);
      color: var(--ink);
      padding: 6px 10px;
      border-radius: 10px;
      cursor: pointer;
      font-family: "IBM Plex Mono", "Courier New", monospace;
    }}
    body.theme-dark .lang-current {{
      border-color: #3d4b66;
    }}
    .lang-options {{
      position: absolute;
      right: 0;
      margin-top: 6px;
      background: var(--card);
      border: 1px solid var(--ink);
      border-radius: 10px;
      box-shadow: 0 10px 24px var(--shadow);
      display: none;
      min-width: 160px;
      z-index: 40;
    }}
    body.theme-dark .lang-options {{
      border-color: #3d4b66;
    }}
    .lang-dropdown.open .lang-options {{
      display: block;
    }}
    .lang-option {{
      width: 100%;
      border: none;
      background: transparent;
      color: var(--ink);
      padding: 8px 10px;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-family: "IBM Plex Mono", "Courier New", monospace;
      text-align: left;
    }}
    .lang-option:hover {{
      background: rgba(0,0,0,0.04);
    }}
    body.theme-dark .lang-option:hover {{
      background: rgba(255,255,255,0.05);
    }}
    .lang-option.active {{
      background: rgba(199, 74, 58, 0.12);
    }}
    body.theme-dark .lang-option.active {{
      background: rgba(199, 74, 58, 0.18);
    }}
    .flag {{
      width: 20px;
      height: 14px;
      display: inline-block;
      background-size: cover;
      background-position: center;
      background-repeat: no-repeat;
      border-radius: 3px;
      border: 1px solid rgba(0,0,0,0.1);
    }}
    .flag-es {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 3 2'%3E%3Crect width='3' height='2' fill='%23c60b1e'/%3E%3Crect y='0.4' width='3' height='1.2' fill='%23ffc400'/%3E%3C/svg%3E");
    }}
    .flag-en {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 3 2'%3E%3Crect width='3' height='2' fill='%23b22234'/%3E%3Cg fill='%23fff'%3E%3Crect y='0.2' width='3' height='0.2'/%3E%3Crect y='0.6' width='3' height='0.2'/%3E%3Crect y='1.0' width='3' height='0.2'/%3E%3Crect y='1.4' width='3' height='0.2'/%3E%3C/g%3E%3Crect width='1.2' height='0.8' fill='%233c3b6e'/%3E%3C/svg%3E");
    }}
    .search-hit {{
      outline: 2px solid #ffb347;
      box-shadow: 0 0 0 3px rgba(255, 179, 71, 0.4);
    }}
    .search-active {{
      outline: 3px solid #ff6b35;
      box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.35);
    }}
    .search-hit-mark {{
      background: #ffbf66;
      color: #111;
      padding: 0 2px;
      border-radius: 4px;
    }}
    .tree-panel {{
      border: 2px solid #e2d8c6;
      background: #fffdf7;
      border-radius: 12px;
      padding: 10px 12px;
      box-shadow: 0 8px 18px rgba(0,0,0,0.08);
      margin: 12px 0;
      max-height: 75vh;
      overflow: auto;
    }}
    body.theme-dark .tree-panel {{
      border-color: #4d607f;
      background: #1c2434;
    }}
    .tree-panel h3 {{
      margin: 0 0 10px;
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 13px;
      color: var(--muted);
    }}
    .calls-list {{
      margin: 6px 0 0 18px;
      padding: 0;
      list-style: disc;
      color: var(--muted);
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
    }}
    body.theme-dark .calls-list {{
      color: #d0d7e6;
    }}
    .calls-stack {{
      display: grid;
      gap: 8px;
      margin-top: 6px;
    }}
    .search-path {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .node {{
      background: linear-gradient(
        135deg,
        hsl(var(--hue), 70%, 94%),
        hsl(var(--hue), 40%, 96%)
      );
      border: 3px solid hsl(var(--hue), 45%, 60%);
      border-radius: 12px;
      padding: 8px 12px 12px;
      margin: 14px 0;
      box-shadow: 0 8px 20px var(--shadow);
    }}
    body.theme-dark .node {{
      background: linear-gradient(135deg, #27344c, #1f2b40);
      border: 2px solid #5a6f96;
      box-shadow: 0 12px 26px rgba(0,0,0,0.30);
    }}
    summary {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      list-style: none;
    }}
    summary::-webkit-details-marker {{
      display: none;
    }}
    .title {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 18px;
      color: #f6f2e8;
      padding: 6px 14px;
      border-radius: 12px;
      background: linear-gradient(135deg, #a2471f, #7f3418);
      box-shadow: 0 6px 14px rgba(0,0,0,0.10);
    }}
    body.theme-dark .title {{
      color: #e8edf7;
      background: linear-gradient(135deg, #365173, #283c59);
      box-shadow: 0 8px 16px rgba(0,0,0,0.22);
    }}
    .summary-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .badge {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 11px;
      color: var(--muted);
      background: #f1e2c9;
      border: 1px solid #e0cfae;
      border-radius: 999px;
      padding: 2px 8px;
    }}
    body.theme-dark .badge {{
      color: #f3eafe;
      background: #40304a;
      border-color: #5a3e68;
    }}
    .badge-error {{
      color: #7a2b1c;
      border-color: #e6b3a6;
      background: #ffeae6;
    }}
    .content {{
      margin-top: 10px;
      display: grid;
      gap: 10px;
    }}
    .field-block {{
      border: 1px dashed #e2d8c6;
      border-radius: 8px;
      padding: 6px 8px;
      background: #fffdf7;
    }}
    body.theme-dark .field-block {{
      border-color: #2d3952;
      background: #131926;
    }}
    .field-label {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
      cursor: pointer;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .field-label::-webkit-details-marker {{
      display: none;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 13px;
      line-height: 1.4;
      font-family: "IBM Plex Mono", "Courier New", monospace;
    }}
    .children {{
      border-left: 4px solid #e2d0b8;
      padding-left: 16px;
      margin-left: 6px;
    }}
    body.theme-dark .children {{
      border-left: 4px solid #25304a;
    }}
    .group {{
      border: 2px dashed hsl(var(--hue), 30%, 70%);
      border-radius: 10px;
      padding: 6px 10px;
      margin: 10px 0;
      background: rgba(255, 255, 255, 0.7);
    }}
    body.theme-dark .group {{
      border-color: #4a5f82;
      background: rgba(46, 60, 86, 0.3);
    }}
    .group-title {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
      cursor: pointer;
      list-style: none;
    }}
    .group-title::-webkit-details-marker {{
      display: none;
    }}
    .group-body {{
      margin-top: 8px;
    }}
    .calls-preview {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
      padding: 6px 0;
    }}
    .panel {{
      background: #fffdf7;
      border: 2px solid #f4ecde;
      border-radius: 12px;
      padding: 10px 12px 12px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.08);
      width: min(520px, 90vw);
    }}
    .panel .panel-body {{
      max-height: 70vh;
      overflow-y: auto;
    }}
    body.theme-dark .panel {{
      background: #161b27;
      border-color: #4d607f;
      box-shadow: 0 12px 28px rgba(0,0,0,0.4);
    }}
    .panel.floating {{
      position: absolute;
      z-index: 20;
    }}
    .panel-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      border-bottom: 1px dashed #e2d8c6;
      padding: 6px 8px 8px;
      margin: -10px -12px 10px;
      background: #fffaf3;
      border-radius: 10px 10px 0 0;
    }}
    body.theme-dark .panel-header {{
      border-bottom-color: #3a4c6b;
      background: #2d384a;
    }}
    .panel-title {{
      font-family: "IBM Plex Mono", "Courier New", monospace;
      font-size: 12px;
      color: var(--muted);
    }}
    .panel-actions {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .panel-btn {{
      width: 26px;
      height: 26px;
      border-radius: 8px;
      border: 1px solid #d8cbbb;
      background: #fffaf3;
      cursor: pointer;
      display: inline-block;
      background-size: 16px 16px;
      background-repeat: no-repeat;
      background-position: center;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }}
    body.theme-dark .panel-btn {{
      border-color: #d8cbbb;
      background-color: #fffaf3;  /* avoid resetting background-position/size so icons stay centered */
    }}
    .panel-btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.12);
    }}
    .btn-minimize {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='6' y='18' width='14' height='2' fill='%23404040'/%3E%3C/svg%3E");
      background-size: 16px 16px;
      background-position: center;
    }}
    .btn-maximize {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='5' y='5' width='14' height='14' rx='2' ry='2' fill='none' stroke='%23404040' stroke-width='2'/%3E%3C/svg%3E");
      background-size: 16px 16px;
      background-position: center;
    }}
    body.theme-dark .btn-minimize {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='6' y='18' width='14' height='2' fill='%23404040'/%3E%3C/svg%3E");
      background-size: 16px 16px;
      background-position: center;
    }}
    body.theme-dark .btn-maximize {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='5' y='5' width='14' height='14' rx='2' ry='2' fill='none' stroke='%23404040' stroke-width='2'/%3E%3C/svg%3E");
      background-size: 16px 16px;
      background-position: center;
    }}
    .panel-close {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath stroke='%23ffffff' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round' d='M6 6l12 12M18 6L6 18'/%3E%3C/svg%3E");
      border: 1px solid #d34f45;
      background-color: #eb6a60;
      background-size: 18px 18px;
      background-repeat: no-repeat;
      background-position: center;
    }}
    body.theme-dark .panel-close {{
      border-color: #d34f45;
      background-color: #eb6a60;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath stroke='%23ffffff' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round' d='M6 6l12 12M18 6L6 18'/%3E%3C/svg%3E");
      background-size: 18px 18px;
      background-position: center;
    }}
    .panel.minimized .panel-body {{
      display: none;
    }}
    .panel-header {{
      cursor: move;
    }}
    .icon {{
      width: 20px;
      height: 20px;
      display: inline-block;
      background-size: 20px 20px;
      background-repeat: no-repeat;
      background-position: center;
    }}
    .icon-in {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%2329a8ab' d='M4 5h10a2 2 0 0 1 2 2v3h-2V7H4v10h10v-3h2v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z'/%3E%3Cpath fill='%2329a8ab' d='M13 8h7v7h-2v-3.586l-5.293 5.293-1.414-1.414L16.586 10H13z'/%3E%3C/svg%3E");
    }}
    .icon-in-after {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23477bff' d='M4 5h10a2 2 0 0 1 2 2v3h-2V7H4v10h10v-3h2v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z'/%3E%3Cpath fill='%23477bff' d='M10 11h4v2h-4z'/%3E%3Cpath fill='%23477bff' d='M13 8h7v7h-2v-3.586l-5.293 5.293-1.414-1.414L16.586 10H13z'/%3E%3C/svg%3E");
    }}
    .icon-out {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23e86b2f' d='M10 5h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10v-2h10V7H10z'/%3E%3Cpath fill='%23e86b2f' d='M11 16H4V8h7v2H6v4h5z'/%3E%3Cpath fill='%23e86b2f' d='M14 12l-3-3v2H7v2h4v2z'/%3E%3C/svg%3E");
    }}
    .icon-calls {{
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23b548f2' d='M7 4h10a2 2 0 0 1 2 2v3h-2V6H7v3H5V6a2 2 0 0 1 2-2z'/%3E%3Cpath fill='%23b548f2' d='M4 11h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2zm0 2v5h16v-5z'/%3E%3Ccircle fill='%23b548f2' cx='8' cy='15.5' r='1.2'/%3E%3Ccircle fill='%23b548f2' cx='12' cy='15.5' r='1.2'/%3E%3Ccircle fill='%23b548f2' cx='16' cy='15.5' r='1.2'/%3E%3C/svg%3E");
    }}
    @media (max-width: 720px) {{
      body {{ padding: 16px; }}
      summary {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <script>
    document.body.classList.add('output-on-demand', 'inputs-on-demand', 'theme-dark');
  </script>
  <header>
    <h1 data-i18n="headerTitle">FlowTrace</h1>
    <div>
      <button type="button" data-i18n="expandAll" onclick="toggleAll(true)">Expandir todo</button>
      <button type="button" data-i18n="collapseAll" onclick="toggleAll(false)">Contraer todo</button>
      <button type="button" id="themeToggle" data-i18n="themeToggleLight" onclick="toggleTheme()">Modo claro</button>
      <div class="lang-dropdown" id="langDropdown">
        <button type="button" class="lang-current" id="langCurrent" aria-haspopup="listbox" aria-expanded="false">
          <span class="flag flag-es"></span><span class="lang-label">Español</span>
        </button>
        <div class="lang-options" id="langOptions" role="listbox">
          <button type="button" class="lang-option active" data-lang="es" onclick="setLang('es')" role="option" aria-selected="true">
            <span class="flag flag-es"></span><span class="lang-label">Español</span>
          </button>
          <button type="button" class="lang-option" data-lang="en" onclick="setLang('en')" role="option" aria-selected="false">
            <span class="flag flag-en"></span><span class="lang-label">English</span>
          </button>
        </div>
      </div>
    </div>
  </header>
  <section class="controls">
    <div class="search-bar">
      <input class="search-input" type="search" placeholder="Buscar..." data-i18n-placeholder="searchPlaceholder" oninput="runSearch(this.value)">
      <button type="button" data-i18n="prev" onclick="prevMatch()">Anterior</button>
      <button type="button" data-i18n="next" onclick="nextMatch()">Siguiente</button>
          <span class="search-count" id="searchCount">0/0</span>
        </div>
        <label><input type="checkbox" checked onchange="toggleClass('no-badges', !this.checked)"> <span data-i18n="showBadges">Mostrar badges</span></label>
        <label><input type="checkbox" checked onchange="toggleClass('hide-badge-module', !this.checked)"> <span data-i18n="badgeModule">Badge module</span></label>
        <label><input type="checkbox" checked onchange="toggleClass('hide-badge-duration', !this.checked)"> <span data-i18n="badgeDuration">Badge duration</span></label>
        <label><input type="checkbox" checked onchange="toggleClass('hide-badge-error', !this.checked)"> <span data-i18n="badgeError">Badge error</span></label>
        <label><input type="checkbox" checked onchange="toggleClass('hide-badge-caller', !this.checked)"> <span data-i18n="badgeCaller">Badge caller</span></label>
        <label><input type="checkbox" checked onchange="toggleClass('hide-badge-memory', !this.checked)"> <span data-i18n="badgeMemory">Badge memory</span></label>
        <label><input type="checkbox" onchange="toggleClass('hide-python-internals', this.checked)"> <span data-i18n="pythonInternals">Ocultar internals Python</span></label>
        <label><input type="checkbox" onchange="toggleClass('output-on-demand', !this.checked)"> <span data-i18n="showOutputs">Mostrar outputs vacios</span></label>
        <label><input type="checkbox" onchange="toggleClass('inputs-on-demand', !this.checked)"> <span data-i18n="showInputs">Mostrar inputs vacios</span></label>
      </section>
  <main>
    {tree}
  </main>
  <script id="tracer-data" type="application/json">{data_json}</script>
  <script>
    const tracerDataEl = document.getElementById('tracer-data');
    const tracerData = tracerDataEl ? JSON.parse(tracerDataEl.textContent) : [];
    const searchIndex = [];
    const searchMap = new Map();
    (function buildIndex() {{
      function walk(node, path, parentId) {{
        const domId = (node && node.id !== undefined && node.id !== null) ? String(node.id) : path;
        let shallow = node;
        if (node && typeof node === 'object') {{
          shallow = Object.assign({{}}, node);
          if (shallow.calls) delete shallow.calls;
        }}
        let searchText = '';
        try {{
          searchText = JSON.stringify(shallow).toLowerCase();
        }} catch (e) {{
          searchText = '';
        }}
        const callable = (node && node.callable ? String(node.callable) : '').toLowerCase();
        const called = (node && node.called ? String(node.called) : '').toLowerCase();
        const entry = {{ domId, node, parentId, path, searchText, callable, called }};
        searchIndex.push(entry);
        searchMap.set(domId, entry);
        if (node && Array.isArray(node.calls)) {{
          node.calls.forEach((child, idx) => {{
            walk(child, path + '.c' + idx, domId);
          }});
        }}
      }}
      if (Array.isArray(tracerData)) {{
        tracerData.forEach((n, i) => walk(n, 'r' + i, null));
      }} else if (tracerData && typeof tracerData === 'object') {{
        walk(tracerData, 'r0', null);
      }}
    }})();
    function toggleAll(open) {{
      document.querySelectorAll('details').forEach((node) => {{
        node.open = open;
      }});
    }}
    function toggleClass(className, add) {{
      document.body.classList.toggle(className, add);
    }}
    function toggleTreeMode() {{}}
    let matches = [];
    let matchIndex = -1;
    let lastQuery = '';
    let currentSearchPanels = [];
    const escapeSelector = (value) => {{
      if (window.CSS && CSS.escape) return CSS.escape(String(value));
      return String(value).replace(/\"/g, '\\"');
    }};
    function buildBreadcrumb(entry) {{
      const labels = [];
      const seen = new Set();
      let cur = entry;
      while (cur && !seen.has(cur.domId)) {{
        seen.add(cur.domId);
        const node = cur.node || {{}};
        let label = node.called || node.callable || String(cur.domId);
        // limpiar __main__ o el script raíz
        if (label === '__main__' || label === node.module || label === (node.script || '')) {{
          label = null;
        }}
        // evitar duplicados consecutivos
        if (label && labels[0] !== label) labels.unshift(label);
        if (cur.parentId === null || cur.parentId === undefined) break;
        cur = searchMap.get(String(cur.parentId));
      }}
      return labels.join(' / ');
    }}
    function findNodeElement(domId) {{
      if (!domId && domId !== 0) return null;
      return document.querySelector('.node[data-node-id=\"' + escapeSelector(String(domId)) + '\"]');
    }}
    function clearSearchHighlights() {{
      document.querySelectorAll('.node.search-hit, .node.search-active').forEach((el) => {{
        el.classList.remove('search-hit', 'search-active');
      }});
    }}
    function escapeHtml(text) {{
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}
    function escapeRegex(text) {{
      return text.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
    }}
    function highlightText(text, needle) {{
      if (!needle) return escapeHtml(text);
      const regex = new RegExp('(' + escapeRegex(needle) + ')', 'gi');
      return escapeHtml(text).replace(regex, '<mark class="search-hit-mark">$1</mark>');
    }}
    function createField(label, value, extraClass = '', iconClass = '') {{
      const details = document.createElement('details');
      details.className = 'field-block ' + extraClass;
      const summary = document.createElement('summary');
      summary.className = 'field-label';
      const icon = document.createElement('span');
      icon.className = 'icon ' + iconClass;
      icon.setAttribute('aria-hidden', 'true');
      summary.appendChild(icon);
      const labelSpan = document.createElement('span');
      labelSpan.innerHTML = highlightText(label, lastQuery);
      summary.appendChild(labelSpan);
      details.appendChild(summary);
      const pre = document.createElement('pre');
      if (value === null || value === undefined) {{
        pre.textContent = 'null';
      }} else if (typeof value === 'object') {{
        try {{
          pre.innerHTML = highlightText(JSON.stringify(value, null, 2), lastQuery);
        }} catch (e) {{
          pre.textContent = String(value);
        }}
      }} else {{
        pre.innerHTML = highlightText(String(value), lastQuery);
      }}
      details.appendChild(pre);
      return details;
    }}
    function renderNodeCard(node, hueSeed = 40) {{
      const details = document.createElement('details');
      details.className = 'node';
      details.open = true;
      const hue = (hueSeed % 360);
      details.style.setProperty('--hue', String(hue));
      const summary = document.createElement('summary');
      const titleSpan = document.createElement('span');
      titleSpan.className = 'title';
      titleSpan.innerHTML = highlightText(node.called || node.callable || 'node', lastQuery);
      summary.appendChild(titleSpan);
      const meta = document.createElement('span');
      meta.className = 'summary-meta';
      if (node.callable && node.callable.startsWith('<')) {{
        details.classList.add('python-internal');
      }}
      const badges = [
        ['badge-module', 'module', node.module],
        ['badge-duration', 'duration_ms', node.duration_ms],
        ['badge-error', 'error', node.error],
        ['badge-caller', 'caller', node.caller],
        ['badge-memory', 'mem', (() => {{
          const before = node.memory_before;
          const after = node.memory_after;
          const pick = (snap) => {{
            if (!snap || typeof snap !== 'object') return null;
            return snap.rss_bytes || snap.py_tracemalloc_current || snap.vms_bytes || snap.py_tracemalloc_peak || null;
          }};
          const b = pick(before);
          const a = pick(after);
          const fmt = (num) => {{
            if (num === null || num === undefined) return null;
            let n = Number(num);
            if (Number.isNaN(n)) return String(num);
            const units = ['B','KB','MB','GB','TB'];
            for (let u of units) {{
              if (Math.abs(n) < 1024 || u === 'TB') return n.toFixed(1) + ' ' + u;
              n /= 1024;
            }}
            return n.toFixed(1) + ' TB';
          }};
          if (b !== null && a !== null) return fmt(b) + '→' + fmt(a);
          if (a !== null) return fmt(a);
          if (b !== null) return fmt(b);
          return null;
        }})()],
      ];
      badges.forEach(([cls, label, val]) => {{
        if (val === undefined || val === null) return;
        const span = document.createElement('span');
        span.className = 'badge ' + cls;
        span.innerHTML = highlightText(label + ': ' + String(val), lastQuery);
        meta.appendChild(span);
      }});
      summary.appendChild(meta);
      details.appendChild(summary);
      const content = document.createElement('div');
      content.className = 'content';
      const inputs = node.inputs || {};
      const inputsAfter = node.inputs_after;
      const output = node.output;
      const error = node.error;
      const inputsField = createField('inputs', inputs, Object.keys(inputs).length ? '' : 'inputs-empty', 'icon-in');
      content.appendChild(inputsField);
      if (inputsAfter !== undefined && JSON.stringify(inputsAfter) !== JSON.stringify(inputs)) {{
        content.appendChild(createField('inputs_after', inputsAfter, '', 'icon-in-after'));
      }}
      const outputClass = (output === null && !error) ? 'output-empty' : '';
      content.appendChild(createField('output', output, outputClass, 'icon-out'));
      const calls = Array.isArray(node.calls) ? node.calls : [];
      if (calls.length) {{
        const callsContainer = document.createElement('details');
        callsContainer.className = 'field-block calls-field';
        callsContainer.open = false;
        const sum = document.createElement('summary');
        sum.className = 'field-label';
        const icon = document.createElement('span');
        icon.className = 'icon icon-calls';
        icon.setAttribute('aria-hidden', 'true');
        sum.appendChild(icon);
        const lbl = document.createElement('span');
        lbl.innerHTML = highlightText('calls (' + calls.length + ')', lastQuery);
        sum.appendChild(lbl);
        callsContainer.appendChild(sum);
        const stack = document.createElement('div');
        stack.className = 'calls-stack';
        calls.forEach((c, idx) => {{
          const childCard = renderNodeCard(c, hueSeed + 25 + idx * 5);
          stack.appendChild(childCard);
        }});
        callsContainer.appendChild(stack);
        content.appendChild(callsContainer);
      }}
      details.appendChild(content);
      return details;
    }}
    function openAncestors(el) {{
      let parent = el.parentElement;
      while (parent) {{
        if (parent.tagName && parent.tagName.toLowerCase() === 'details') {{
          parent.open = true;
        }}
        parent = parent.parentElement;
      }}
    }}
    function closeSearchPanels() {{
      currentSearchPanels.forEach((p) => closePanel(p));
      currentSearchPanels = [];
    }}
    function closeTreePanel() {{
      const tree = document.getElementById('searchTreePanel');
      if (tree) tree.remove();
    }}
    function displayTitleFor(entry) {{
      const node = entry && entry.node;
      if (node && node.caller) {{
        let c = String(node.caller);
        if (c.includes('::')) c = c.split('::').pop();
        if (c === '__main__') c = null;
        if (c) return c;
      }}
      if (node && node.callable) return node.callable;
      if (node && node.called) return node.called;
      return 'Match';
    }}
    function createSearchPanel(entry, left, top) {{
      const panel = document.createElement('div');
      panel.className = 'panel floating';
      panel.setAttribute('data-search-id', entry.domId);
      const title = displayTitleFor(entry);
      panel.innerHTML =
        '<div class="panel-header">' +
        '<div class="panel-title">' + title + '</div>' +
        '<div class="panel-actions">' +
        '<button class="panel-btn btn-minimize" type="button" aria-label="Minimize"></button>' +
        '<button class="panel-btn btn-maximize" type="button" aria-label="Maximize"></button>' +
        '<button class="panel-btn panel-close" type="button" aria-label="Close"></button>' +
        '</div>' +
        '</div>' +
        '<div class="panel-body"></div>';
      const body = panel.querySelector('.panel-body');
      const el = findNodeElement(entry.domId);
      if (el) {{
        const clone = el.cloneNode(true);
        clone.querySelectorAll('details').forEach((d) => (d.open = true));
        body.appendChild(clone);
      }} else {{
        const card = renderNodeCard(entry.node);
        body.appendChild(card);
      }}
      const btnClose = panel.querySelector('.panel-close');
      const btnMin = panel.querySelector('.btn-minimize');
      const btnMax = panel.querySelector('.btn-maximize');
      btnClose.addEventListener('click', () => {{
        currentSearchPanels = currentSearchPanels.filter((p) => p !== panel);
        closePanel(panel);
      }});
      btnMin.addEventListener('click', () => {{
        panel.classList.toggle('minimized');
      }});
      btnMax.addEventListener('click', () => {{
        panel.classList.remove('minimized');
        const maximized = panel.classList.toggle('maximized');
        if (maximized) {{
          panel.dataset.prevLeft = panel.style.left || '';
          panel.dataset.prevTop = panel.style.top || '';
          panel.dataset.prevWidth = panel.style.width || '';
          panel.dataset.prevHeight = panel.style.height || '';
          panel.style.left = (window.scrollX + 10) + 'px';
          panel.style.top = (window.scrollY + 20) + 'px';
          panel.style.width = '90vw';
          panel.style.height = '80vh';
        }} else {{
          panel.style.left = panel.dataset.prevLeft || panel.style.left;
          panel.style.top = panel.dataset.prevTop || panel.style.top;
          panel.style.width = panel.dataset.prevWidth || '';
          panel.style.height = panel.dataset.prevHeight || '';
        }}
      }});
      document.body.appendChild(panel);
      bringToFront(panel);
      // posicionamiento se recibe por argumento (left, top)
      panel.style.left = left + 'px';
      panel.style.top = top + 'px';
      const header = panel.querySelector('.panel-header');
      let dragging = false;
      let offsetX = 0;
      let offsetY = 0;
      header.addEventListener('mousedown', (e) => {{
        dragging = true;
        offsetX = e.clientX - panel.offsetLeft;
        offsetY = e.clientY - panel.offsetTop;
        bringToFront(panel);
      }});
      document.addEventListener('mousemove', (e) => {{
        if (!dragging) return;
        panel.style.left = (e.clientX - offsetX) + 'px';
        panel.style.top = (e.clientY - offsetY) + 'px';
      }});
      document.addEventListener('mouseup', () => {{
        dragging = false;
      }});
      currentSearchPanels.push(panel);
      return {{ w: panel.offsetWidth || 360, h: panel.offsetHeight || 260 }};
    }}
function openSearchPanel(entry) {{
      if (!entry) return;
      closeSearchPanels();
      const baseLeft = window.scrollX + 32;
      const baseTop = window.scrollY + 160;
      createSearchPanel(entry, baseLeft, baseTop);
    }}
    function runSearch(query) {{
      clearSearchHighlights();
      closeSearchPanels();
      matches = [];
      matchIndex = -1;
      lastQuery = query;
      if (!query) {{
        updateCount();
        return;
      }}
      const needle = query.toLowerCase();
      matches = searchIndex
        .filter((entry) => {{
          if (!entry.callable && !entry.called) return false;
          const callable = entry.callable || '';
          const called = entry.called || '';
          return callable.includes(needle) || called.includes(needle);
        }})
        .map((entry) => {{
          const callable = entry.callable || '';
          const called = entry.called || '';
          const score = callable.includes(needle) ? 10 : 8;
          return Object.assign({{}}, entry, {{ score }});
        }})
        .sort((a, b) => b.score - a.score);
      matches.forEach((entry) => {{
        const el = findNodeElement(entry.domId);
        if (el) el.classList.add('search-hit');
      }});
      if (matches.length) {{
        matchIndex = 0;
        focusMatch();
      }}
      updateCount();
    }}
    function focusMatch() {{
      document.querySelectorAll('.node.search-active').forEach((el) => el.classList.remove('search-active'));
      if (matchIndex < 0 || matchIndex >= matches.length) {{
        updateCount();
        return;
      }}
      const entry = matches[matchIndex];
      const nodeEl = findNodeElement(entry.domId);
      if (nodeEl) {{
        nodeEl.classList.add('search-active');
        nodeEl.open = true;
        openAncestors(nodeEl);
        nodeEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
      openSearchPanel(entry);
      updateCount();
    }}
    function nextMatch() {{
      if (!matches.length) return;
      matchIndex = (matchIndex + 1) % matches.length;
      focusMatch();
    }}
    function prevMatch() {{
      if (!matches.length) return;
      matchIndex = (matchIndex - 1 + matches.length) % matches.length;
      focusMatch();
    }}
    function updateCount() {{
      const el = document.getElementById('searchCount');
      const total = matches.length;
      const current = total ? matchIndex + 1 : 0;
      el.textContent = current + "/" + total;
    }}
    let zCounter = 50;
    function bringToFront(el) {{
      if (!el || !el.style) return;
      zCounter += 1;
      el.style.zIndex = zCounter;
    }}
    document.addEventListener('mousedown', (event) => {{
      const panel = event.target.closest('.panel');
      if (panel) {{
        bringToFront(panel);
      }}
    }});
    const translations = {{
      es: {{
        headerTitle: 'FlowTrace',
        expandAll: 'Expandir todo',
        collapseAll: 'Contraer todo',
        treeMode: 'Modo árbol',
        treeModeOn: 'Modo árbol (ON)',
        treeTitle: 'Ruta de llamadas',
        themeToggleLight: 'Modo claro',
        themeToggleDark: 'Modo oscuro',
        searchPlaceholder: 'Buscar...',
        prev: 'Anterior',
        next: 'Siguiente',
        showBadges: 'Mostrar badges',
        badgeModule: 'Badge module',
        badgeDuration: 'Badge duration',
        badgeError: 'Badge error',
        badgeCaller: 'Badge caller',
        badgeMemory: 'Badge memoria',
        pythonInternals: 'Ocultar internals Python',
        showOutputs: 'Mostrar outputs vacios',
        showInputs: 'Mostrar inputs vacios',
        callsPreview: 'Abrir llamadas',
        calls: 'Llamadas',
        panelCalls: 'Llamadas',
        close: 'Cerrar',
      }},
      en: {{
        headerTitle: 'FlowTrace',
        expandAll: 'Expand all',
        collapseAll: 'Collapse all',
        treeMode: 'Tree mode',
        treeModeOn: 'Tree mode (ON)',
        treeTitle: 'Call path',
        themeToggleLight: 'Light mode',
        themeToggleDark: 'Dark mode',
        searchPlaceholder: 'Search...',
        prev: 'Previous',
        next: 'Next',
        showBadges: 'Show badges',
        badgeModule: 'Badge module',
        badgeDuration: 'Badge duration',
        badgeError: 'Badge error',
        badgeCaller: 'Badge caller',
        badgeMemory: 'Memory badge',
        showOutputs: 'Show empty outputs',
        showInputs: 'Show empty inputs',
        callsPreview: 'Open calls',
        calls: 'Calls',
        panelCalls: 'Calls',
        close: 'Close',
      }},
    }};
    let currentLang = 'es';
    function applyTranslations() {{
      const t = translations[currentLang];
      document.querySelectorAll('[data-i18n]').forEach((el) => {{
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.textContent = t[key];
      }});
      document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {{
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key]) el.setAttribute('placeholder', t[key]);
      }});
      document.querySelectorAll('.field-label[data-i18n-label]').forEach((el) => {{
        const key = el.getAttribute('data-i18n-label');
        const count = el.getAttribute('data-count');
        const icon = el.querySelector('.icon');
        const text = t[key] ? t[key] : el.textContent;
        el.innerHTML = '';
        if (icon) el.appendChild(icon);
        el.append(document.createTextNode(count ? (text + ' (' + count + ')') : text));
      }});
      document.querySelectorAll('.calls-preview[data-i18n]').forEach((el) => {{
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.textContent = t[key];
      }});
      document.querySelectorAll('.panel-title').forEach((el) => {{
        const base = el.getAttribute('data-title-key');
        if (base && t[base]) el.textContent = t[base];
      }});
      const themeBtn = document.getElementById('themeToggle');
      if (themeBtn) {{
        const dark = document.body.classList.contains('theme-dark');
        themeBtn.textContent = dark ? t.themeToggleLight : t.themeToggleDark;
      }}
      document.title = t.headerTitle || document.title;
    }}
    function setLang(lang) {{
      currentLang = lang === 'en' ? 'en' : 'es';
      document.querySelectorAll('.lang-option').forEach((opt) => {{
        const active = opt.getAttribute('data-lang') === currentLang;
        opt.classList.toggle('active', active);
        opt.setAttribute('aria-selected', active ? 'true' : 'false');
      }});
      const btn = document.getElementById('langCurrent');
      if (btn) {{
        const label = currentLang === 'en' ? 'English' : 'Español';
        const flag = currentLang === 'en' ? 'flag-en' : 'flag-es';
        btn.innerHTML = '<span class=\"flag ' + flag + '\"></span><span class=\"lang-label\">' + label + '</span>';
        btn.setAttribute('aria-expanded', 'false');
      }}
      const dropdown = document.getElementById('langDropdown');
      if (dropdown) dropdown.classList.remove('open');
      applyTranslations();
    }}
    function toggleTheme() {{
      const body = document.body;
      const dark = !body.classList.contains('theme-dark');
      body.classList.toggle('theme-dark', dark);
      applyTranslations();
    }}
    document.addEventListener('click', (event) => {{
      const langBtn = event.target.closest('.lang-current');
      const langOpt = event.target.closest('.lang-option');
      if (langBtn) {{
        const dropdown = document.getElementById('langDropdown');
        const expanded = dropdown.classList.toggle('open');
        langBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        return;
      }}
      if (langOpt) {{
        setLang(langOpt.getAttribute('data-lang'));
        const dropdown = document.getElementById('langDropdown');
        dropdown.classList.remove('open');
        const lc = document.getElementById('langCurrent');
        if (lc) lc.setAttribute('aria-expanded', 'false');
        return;
      }}
      const dropdown = document.getElementById('langDropdown');
      if (dropdown && !dropdown.contains(event.target)) {{
        dropdown.classList.remove('open');
        const lc = document.getElementById('langCurrent');
        if (lc) lc.setAttribute('aria-expanded', 'false');
      }}
      const summary = event.target.closest('.calls-field > summary');
      if (!summary) return;
      const field = summary.parentElement;
      const callsId = field.getAttribute('data-calls-id');
      if (!callsId) {
        // cards generadas en búsqueda: permitir toggle nativo
        return;
      }
      event.preventDefault();
      const t = translations[currentLang] || translations.es;
      const title = field.getAttribute('data-calls-title') || (t.calls || 'Calls');
      const template = document.getElementById(callsId);
      if (!template) return;
      const existing = document.querySelector('.panel[data-calls-id="' + callsId + '"]');
      if (existing) {{
        closePanel(existing);
        return;
      }}
      const panel = document.createElement('div');
      panel.className = 'panel floating';
      panel.setAttribute('data-calls-id', callsId);
      const parentPanel = summary.closest('.panel');
      if (parentPanel) {{
        const parentId = parentPanel.getAttribute('data-calls-id');
        if (parentId) {{
          panel.setAttribute('data-parent-id', parentId);
        }}
      }}
      panel.innerHTML =
        '<div class="panel-header">' +
        '<div class="panel-title" data-title-key="panelCalls">' + (t.panelCalls || 'Calls') + '</div>' +
        '<div class="panel-actions">' +
        '<button class="panel-btn btn-minimize" type="button" aria-label="Minimize"></button>' +
        '<button class="panel-btn btn-maximize" type="button" aria-label="Maximize"></button>' +
        '<button class="panel-btn panel-close" type="button" aria-label="Close"></button>' +
        '</div>' +
        '</div>' +
        '<div class="panel-body"></div>';
      panel.querySelector('.panel-body').appendChild(template.content.cloneNode(true));
      const btnClose = panel.querySelector('.panel-close');
      const btnMin = panel.querySelector('.btn-minimize');
      const btnMax = panel.querySelector('.btn-maximize');
      btnClose.addEventListener('click', () => closePanel(panel));
      btnMin.addEventListener('click', () => {{
        panel.classList.toggle('minimized');
      }});
      btnMax.addEventListener('click', () => {{
        // al maximizar, aseguramos que no esté minimizada
        panel.classList.remove('minimized');
        const maximized = panel.classList.toggle('maximized');
        if (maximized) {{
          panel.dataset.prevLeft = panel.style.left || '';
          panel.dataset.prevTop = panel.style.top || '';
          panel.dataset.prevWidth = panel.style.width || '';
          panel.dataset.prevHeight = panel.style.height || '';
          panel.style.left = (window.scrollX + 10) + 'px';
          panel.style.top = (window.scrollY + 20) + 'px';
          panel.style.width = '90vw';
          panel.style.height = '80vh';
        }} else {{
          panel.style.left = panel.dataset.prevLeft || panel.style.left;
          panel.style.top = panel.dataset.prevTop || panel.style.top;
          panel.style.width = panel.dataset.prevWidth || '';
          panel.style.height = panel.dataset.prevHeight || '';
        }}
      }});
      document.body.appendChild(panel);
      bringToFront(panel);
      positionPanel(panel, field);
      panel.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      const header = panel.querySelector('.panel-header');
      let dragging = false;
      let offsetX = 0;
      let offsetY = 0;
      header.addEventListener('mousedown', (e) => {{
        dragging = true;
        offsetX = e.clientX - panel.offsetLeft;
        offsetY = e.clientY - panel.offsetTop;
        bringToFront(panel);
      }});
      document.addEventListener('mousemove', (e) => {{
        if (!dragging) return;
        panel.style.left = (e.clientX - offsetX) + 'px';
        panel.style.top = (e.clientY - offsetY) + 'px';
      }});
      document.addEventListener('mouseup', () => {{
        dragging = false;
      }});
    }});
    function closePanel(panel) {{
      const id = panel.getAttribute('data-calls-id');
      if (id) {{
        document
          .querySelectorAll('.panel[data-parent-id=\"' + id + '\"]')
          .forEach((child) => closePanel(child));
      }}
      panel.remove();
    }}
    function positionPanel(panel, field) {{
      const openPanels = Array.from(document.querySelectorAll('.panel'));
      const isFirst = openPanels.length === 1; // solo el que estamos colocando
      const rectField = field.getBoundingClientRect();
      const parentPanel = field.closest('.panel');
      if (parentPanel && parentPanel.classList.contains('maximized')) {{
        const parentRect = parentPanel.getBoundingClientRect();
        panel.style.left = (parentRect.left + parentRect.width / 2 - panel.offsetWidth / 2) + window.scrollX + 'px';
        panel.style.top = (parentRect.top + parentRect.height / 2 - panel.offsetHeight / 2) + window.scrollY + 'px';
        return;
      }}
      let top = rectField.bottom + window.scrollY + 8;
      if (parentPanel) {{
        const parentRect = parentPanel.getBoundingClientRect();
        top = parentRect.top + window.scrollY;
      }}
      let left = rectField.left + window.scrollX;
      if (!isFirst) {{
        let rightMost = rectField.right + window.scrollX;
        openPanels.forEach((p) => {{
          if (p === panel) return;
          const rect = p.getBoundingClientRect();
          rightMost = Math.max(rightMost, rect.left + rect.width + window.scrollX);
        }});
        left = rightMost + 12;
        const viewportRight = window.scrollX + window.innerWidth;
        const panelWidth = panel.offsetWidth || 320;
        if (left + panelWidth > viewportRight - 12) {{
          left = rectField.left + window.scrollX;
          if (parentPanel) {{
            const parentRect = parentPanel.getBoundingClientRect();
            top = parentRect.top + window.scrollY + parentRect.height / 2;
          }} else {{
            top = rectField.bottom + window.scrollY + 24;
          }}
        }}
      }}
      panel.style.left = left + 'px';
      panel.style.top = top + 'px';
    }}
    setLang('en');
  </script>
</body>
</html>"""
    template = template.replace("{tree}", "__TREE__").replace("{data_json}", "__DATA__")
    template = template.replace("{{", "{").replace("}}", "}")
    return template.replace("__TREE__", tree).replace("__DATA__", data_json)


def _parse_args():
    parser = argparse.ArgumentParser(description="Tracerado JSON visualizer")
    parser.add_argument(
        "-i",
        "--input",
        default="flowtrace.json",
        help="Ruta del JSON generado por flowtrace",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="flowtrace.html",
        help="Ruta del HTML de salida",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html_doc = _render_html(data)
    Path(args.output).write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
