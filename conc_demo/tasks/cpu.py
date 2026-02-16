from concurrent.futures import ProcessPoolExecutor
from math import factorial


def heavy_factorial(n: int) -> int:
    return factorial(n)


def run_cpu_batch(nums: list[int]) -> list[int]:
    with ProcessPoolExecutor() as pool:
        return list(pool.map(heavy_factorial, nums))
