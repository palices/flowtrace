from typing import Iterable, List

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def moving_average(values: Iterable[float], window: int = 3) -> List[float]:
    values = list(values)
    if not values:
        return []
    out = []
    for i in range(len(values)):
        left = max(0, i - window + 1)
        window_vals = values[left : i + 1]
        out.append(sum(window_vals) / len(window_vals))
    return out
