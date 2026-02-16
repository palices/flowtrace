from pathlib import Path
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
