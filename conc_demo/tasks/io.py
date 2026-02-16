import time
from concurrent.futures import ThreadPoolExecutor
from demo.common.logger import trace_call


def fake_io(name: str, delay: float = 0.1) -> dict:
    time.sleep(delay)
    return trace_call('fake_io', {'name': name, 'delay': delay})


def run_io_batch(items: list[str], delay: float = 0.1) -> list[dict]:
    with ThreadPoolExecutor(max_workers=min(8, len(items) or 1)) as pool:
        return list(pool.map(lambda x: fake_io(x, delay), items))
