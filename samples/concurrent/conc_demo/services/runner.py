from pathlib import Path
from samples.concurrent.conc_demo.tasks.cpu import run_cpu_batch
from samples.concurrent.conc_demo.tasks.io import run_io_batch
from samples.concurrent.conc_demo.common.log import log, save_log


def run_pipeline(numbers: list[int], names: list[str], log_path: Path) -> dict:
    cpu_results = run_cpu_batch(numbers)
    io_results = run_io_batch(names, delay=0.05)
    report_lines = [log(f"cpu for {n} = {r}") for n, r in zip(numbers, cpu_results)]
    report_lines += [log(f"io for {res['payload']['name']} delay={res['payload']['delay']}") for res in io_results]
    save_log(log_path, report_lines)
    total = sum(cpu_results) + sum(res['payload']['delay'] for res in io_results)
    return {
        'cpu': cpu_results,
        'io': io_results,
        'logfile': str(log_path),
        'total': total,
    }
