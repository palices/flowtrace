from demo.common.logger import trace_call
from demo.common.math_utils import clamp

def vat(amount: float, rate: float = 0.21) -> float:
    taxed = amount * rate
    return clamp(taxed, 0, amount * 2)


def apply_tax_line(item: dict, rate: float = 0.21) -> dict:
    result = item.copy()
    result['tax'] = vat(item['subtotal'], rate)
    result['total'] = result['subtotal'] + result['tax']
    return trace_call('apply_tax_line', result)
