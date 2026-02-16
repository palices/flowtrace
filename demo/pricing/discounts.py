from demo.common.logger import trace_call
from demo.common.math_utils import clamp


def bulk_discount(subtotal: float, items: int) -> float:
    base = 0.05 if items >= 3 else 0.0
    extra = 0.02 if subtotal > 50 else 0.0
    return clamp(subtotal * (base + extra), 0, subtotal * 0.3)


def loyalty_discount(subtotal: float, points: int) -> float:
    factor = min(points / 1000, 0.1)
    return clamp(subtotal * factor, 0, subtotal * 0.15)


def apply_discounts(item: dict, points: int = 0) -> dict:
    result = item.copy()
    result['discounts'] = {
        'bulk': bulk_discount(item['subtotal'], item['qty']),
        'loyalty': loyalty_discount(item['subtotal'], points),
    }
    result['subtotal'] = item['subtotal'] - sum(result['discounts'].values())
    return trace_call('apply_discounts', result)
