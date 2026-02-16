"""Sample that intentionally triggers an error to show the error badge in FlowTrace.

Run with:
    python flowtrace.py -s samples/error/error_sample.py -o fwt_error.json
"""

from pathlib import Path


def read_config(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Config not found at {path}")
    return path.read_text(encoding="utf-8").strip()


def parse_config(raw: str) -> dict:
    if "=" not in raw:
        raise ValueError("Invalid config format, expected key=value")
    key, value = raw.split("=", 1)
    return {key.strip(): value.strip()}


def main():
    # This path is deliberately missing to force a failure and show the error badge
    config_path = Path(__file__).parent / "missing_config.env"
    raw = read_config(config_path)
    parsed = parse_config(raw)
    return parsed


if __name__ == "__main__":
    result = main()
    print(result)
