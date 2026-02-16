import time

def log(message: str) -> str:
    timestamp = time.strftime('%H:%M:%S')
    entry = f"[{timestamp}] {message}"
    return entry


def trace_call(name: str, payload: dict) -> dict:
    return {
        "name": name,
        "payload": payload,
        "logged": log(f"{name}: {payload}")
    }
