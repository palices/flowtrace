"""Ejemplo FlowTrace con argumentos posicionales.

Uso:
    python flowtrace.py -s samples/basic/basic_positional_sample.py "juan perez" gold 2 1 0 0.18
Posicionales:
    customer   nombre del cliente
    tier       gold|silver|none
    coffee     cantidad de cafes
    cake       cantidad de tortas
    tea        cantidad de tes
    tax        (opcional) tasa de impuesto, default 0.21
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from samples.basic.basic_sample import (
    Item,
    Inventory,
    PricingService,
    OrderService,
    seed_inventory,
)


def create_items_from_positional(coffee_qty, cake_qty, tea_qty):
    price_map = {"coffee": 3.5, "tea": 2.1, "cake": 4.25}
    items = []
    if coffee_qty:
        items.append(Item(name="coffee", price=price_map["coffee"], quantity=coffee_qty))
    if cake_qty:
        items.append(Item(name="cake", price=price_map["cake"], quantity=cake_qty))
    if tea_qty:
        items.append(Item(name="tea", price=price_map["tea"], quantity=tea_qty))
    return items


def parse_positional_args():
    parser = argparse.ArgumentParser(
        description="Basic FlowTrace sample con argumentos posicionales"
    )
    parser.add_argument("customer", help="Nombre del cliente")
    parser.add_argument(
        "tier",
        choices=["gold", "silver", "none"],
        nargs="?",
        default="gold",
        help="Nivel de descuento (default gold)",
    )
    parser.add_argument(
        "coffee",
        type=int,
        nargs="?",
        default=2,
        help="Cantidad de cafes (default 2)",
    )
    parser.add_argument(
        "cake",
        type=int,
        nargs="?",
        default=1,
        help="Cantidad de tortas (default 1)",
    )
    parser.add_argument(
        "tea",
        type=int,
        nargs="?",
        default=0,
        help="Cantidad de tes (default 0)",
    )
    parser.add_argument(
        "tax",
        type=float,
        nargs="?",
        default=0.21,
        help="Tasa de impuesto (opcional, default 0.21)",
    )
    return parser.parse_args()


def run_positional_flow(customer, tier, coffee, cake, tea, tax):
    inventory = Inventory()
    seed_inventory(inventory)
    pricing = PricingService(tax_rate=tax)
    service = OrderService(inventory, pricing)
    items = create_items_from_positional(coffee, cake, tea)
    return service.place_order(customer, items, tier=tier)


if __name__ == "__main__":
    args = parse_positional_args()
    confirmation = run_positional_flow(
        customer=args.customer,
        tier=args.tier,
        coffee=args.coffee,
        cake=args.cake,
        tea=args.tea,
        tax=args.tax,
    )
    print(confirmation)
