import sys
from pathlib import Path

# ensure project root on sys.path when running directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conc_demo.services.runner import run_pipeline


def main():
    numbers = [12, 10, 8, 6]
    names = ['alpha', 'beta', 'gamma', 'delta']
    log_path = Path('conc_demo/output.log')
    result = run_pipeline(numbers, names, log_path)
    print('Pipeline total:', result['total'])
    print('Log saved to', result['logfile'])


if __name__ == '__main__':
    main()
