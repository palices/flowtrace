"""
Nested multiprocessing worker: spawns its own subprocess pool.
Used to test autotrace in multi-level process trees.
"""

from __future__ import annotations

import argparse
from multiprocessing import Process, Pool, Manager
import mp_worker  # type: ignore


def run_inner(inner_jobs: int, iterations: int) -> list[float]:
    with Pool(processes=inner_jobs) as pool:
        return pool.map(mp_worker.compute, [iterations] * inner_jobs)


def run_outer(inner_jobs: int, iterations: int, out_list: list, idx: int):
    out_list[idx] = run_inner(inner_jobs, iterations)


def main(outer_jobs: int, inner_jobs: int, iterations: int):
    with Manager() as manager:
        manager_results = manager.list([None] * outer_jobs)
        procs: list[Process] = []
        for i in range(outer_jobs):
            p = Process(target=run_outer, args=(inner_jobs, iterations, manager_results, i))
            p.daemon = False  # allow spawning children
            procs.append(p)
            p.start()
        for p in procs:
            p.join()
        print(f"nested_results={list(manager_results)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outer-jobs", type=int, default=2)
    parser.add_argument("--inner-jobs", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=20000)
    args = parser.parse_args()
    main(args.outer_jobs, args.inner_jobs, args.iterations)
