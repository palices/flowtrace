from samples.complex.demo.common.logger import trace_call

PRODUCTS = {
    'coffee': {'price': 3.5},
    'tea': {'price': 2.9},
    'cookie': {'price': 1.2},
}


def get_product(name: str) -> dict:
    data = PRODUCTS.get(name, {'price': 0})
    return trace_call('get_product', {'name': name, 'price': data['price']})


def list_products():
    return trace_call('list_products', PRODUCTS)
