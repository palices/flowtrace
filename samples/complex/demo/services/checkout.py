from samples.complex.demo.common.logger import trace_call
from samples.complex.demo.repository.products import get_product
from samples.complex.demo.pricing.discounts import apply_discounts
from samples.complex.demo.pricing.tax import apply_tax_line


def price_line(name: str, qty: int, loyalty_points: int = 0) -> dict:
    product = get_product(name)
    subtotal = product['payload']['price'] * qty
    enriched = {'name': name, 'qty': qty, 'subtotal': subtotal}
    discounts = apply_discounts(enriched, loyalty_points)
    taxed = apply_tax_line(discounts['payload'], rate=0.21)
    taxed['payload']['trace'] = {
        'product': product['payload'],
        'discounts': discounts['payload'],
    }
    return trace_call('price_line', taxed['payload'])


def checkout(lines: list[tuple[str, int]], loyalty_points: int = 0) -> dict:
    detailed = [price_line(name, qty, loyalty_points) for name, qty in lines]
    total = sum(line['payload']['total'] for line in detailed)
    return trace_call('checkout', {
        'lines': detailed,
        'total': total,
        'loyalty_points': loyalty_points,
    })
