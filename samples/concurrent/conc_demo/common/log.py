import time
from pathlib import Path

def log(msg: str) -> str:
    ts = time.strftime('%H:%M:%S')
    return f"[{ts}] {msg}"


def save_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
