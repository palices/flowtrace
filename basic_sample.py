from dataclasses import dataclass


def clamp(value, low, high):
    return max(low, min(high, value))


def apply_tax(amount, rate):
    return round(amount * (1 + rate), 2)


def normalize_name(name):
    return " ".join(part.capitalize() for part in name.strip().split())


def calculate_discount(total, tier):
    if tier == "gold":
        return total * 0.15
    if tier == "silver":
        return total * 0.08
    return 0.0


@dataclass
class Item:
    name: str
    price: float
    quantity: int


class Inventory:
    def __init__(self):
        self._stock = {}

    def add(self, item, count):
        current = self._stock.get(item, 0)
        self._stock[item] = current + count
        return self._stock[item]

    def reserve(self, item, count):
        available = self._stock.get(item, 0)
        if count > available:
            raise ValueError("not enough stock")
        self._stock[item] = available - count
        return count


class PricingService:
    def __init__(self, tax_rate):
        self.tax_rate = tax_rate

    def subtotal(self, items):
        return sum(item.price * item.quantity for item in items)

    def total_with_tax(self, items, tier):
        base = self.subtotal(items)
        discount = calculate_discount(base, tier)
        discounted = clamp(base - discount, 0, base)
        return apply_tax(discounted, self.tax_rate)


class OrderService:
    def __init__(self, inventory, pricing):
        self.inventory = inventory
        self.pricing = pricing

    def _reserve_items(self, items):
        for item in items:
            self.inventory.reserve(item.name, item.quantity)

    def _build_confirmation(self, customer, total):
        customer_name = normalize_name(customer)
        return f"Order for {customer_name} confirmed: ${total}"

    def place_order(self, customer, items, tier):
        self._reserve_items(items)
        total = self.pricing.total_with_tax(items, tier)
        return self._build_confirmation(customer, total)


def seed_inventory(inventory):
    inventory.add("coffee", 20)
    inventory.add("tea", 15)
    inventory.add("cake", 10)


def create_items():
    return [
        Item(name="coffee", price=3.5, quantity=2),
        Item(name="cake", price=4.25, quantity=1),
    ]


def run_order_flow():
    inventory = Inventory()
    seed_inventory(inventory)
    pricing = PricingService(tax_rate=0.21)
    service = OrderService(inventory, pricing)
    items = create_items()
    return service.place_order("  ana maria  ", items, tier="gold")


if __name__ == "__main__":
    confirmation = run_order_flow()
    print(confirmation)
