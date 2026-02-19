import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for h in values:
        if "=" not in h:
            sys.stderr.write(f"[export-otlp] Ignoring header '{h}' (expected key=value)\n")
            continue
        k, v = h.split("=", 1)
        headers[k.strip()] = v.strip()
    return headers


def load_root(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or not isinstance(data, list):
        raise ValueError("Invalid FlowTrace JSON: expected list with root node")
    return data[0]


def emit_tree(tracer, node: dict[str, Any], parent_ctx=None) -> None:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    callable_name = node.get("callable")
    called_name = node.get("called")

    if callable_name and called_name and callable_name != called_name:
        span_name = f"{called_name}.{callable_name}"
    else:
        span_name = callable_name or called_name or "unknown"

    if node.get("module"):
        span_name = f"{node['module']}::{span_name}"
    if node.get("instance_id") is not None:
        span_name += f"#{node['instance_id']}"

    with tracer.start_as_current_span(span_name, context=parent_ctx) as span:
        span.set_attribute("flowtrace.module", node.get("module", ""))
        span.set_attribute("flowtrace.called", node.get("called", ""))
        if node.get("duration_ms") is not None:
            span.set_attribute("flowtrace.duration_ms", node.get("duration_ms"))
        if node.get("instance_id") is not None:
            span.set_attribute("flowtrace.instance_id", node.get("instance_id"))
        if node.get("inputs"):
            span.set_attribute("flowtrace.inputs_present", True)
        if node.get("error"):
            span.record_exception(Exception(str(node.get("error"))))
            span.set_status(Status(StatusCode.ERROR))
        child_ctx = trace.set_span_in_context(span)
        for child in node.get("calls", []):
            emit_tree(tracer, child, child_ctx)


def export_otlp(json_path: Path, endpoint: str, service_name: str | None, headers: dict[str, str]) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"[export-otlp] Missing dependency opentelemetry-* ({exc})\n")
        sys.exit(1)

    root = load_root(json_path)
    resource = Resource.create({"service.name": service_name or json_path.stem})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("flowtrace.exporter")

    try:
        emit_tree(tracer, root)
    finally:
        provider.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Export FlowTrace JSON to OTLP/HTTP")
    parser.add_argument("-i", "--input", default="flowtrace.json", help="Path to FlowTrace JSON")
    parser.add_argument("--endpoint", required=True, help="OTLP/HTTP endpoint (e.g. http://localhost:4318/v1/traces)")
    parser.add_argument("--service", default=None, help="service.name value (defaults to JSON filename)")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra OTLP header key=value (repeatable)",
    )
    args = parser.parse_args()

    headers = parse_headers(args.header)
    export_otlp(Path(args.input), args.endpoint, args.service, headers)


if __name__ == "__main__":
    main()
