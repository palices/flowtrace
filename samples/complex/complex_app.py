import sys
from pathlib import Path

# ensure project root is on sys.path when executed directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from samples.complex.demo.services.checkout import checkout


def main():
    cart = [('coffee', 2), ('cookie', 4), ('tea', 1)]
    result = checkout(cart, loyalty_points=350)
    # imprimimos resumen simple
    print(f"TOTAL: {result['payload']['total']:.2f}")
    for line in result['payload']['lines']:
        print(f"- {line['payload']['name']} x{line['payload']['qty']} -> {line['payload']['total']:.2f}")


if __name__ == '__main__':
    main()
