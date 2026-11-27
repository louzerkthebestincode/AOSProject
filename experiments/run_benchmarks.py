from __future__ import annotations

import csv
import json
from pathlib import Path
import time

from src.deadlock_simulator.concurrency.runner import SimulationRunner, WorkerSpec
from src.deadlock_simulator.core.resource_manager import ResourceManager
from src.deadlock_simulator.logging_config import configure_logging


def run_benchmarks() -> None:
    configure_logging("logs/benchmarks.log")
    results_dir = Path("experiments/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "process_counts": [2, 5, 10, 15, 20],
        "hold_delay_s": 0.4,
        "work_delay_s": 0.1,
        "check_interval_s": 0.15,
        "timeout_s": 15.0,
    }
    (results_dir / "params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")

    csv_path = results_dir / "experimental_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "nb_processus",
            "temps_detection_dfs_ms",
            "temps_recuperation_ms",
            "temps_total_simulation_s",
            "victimes_sacrifiees",
            "processus_termines_succes",
        ])

        for n in params["process_counts"]:
            resources = {f"R{i:02d}": 1 for i in range(1, n + 1)}
            res_names = list(resources.keys())
            rm = ResourceManager(resources)
            specs = [
                WorkerSpec(
                    f"P{i + 1:02d}",
                    [res_names[i], res_names[(i + 1) % n]],
                    hold_delay=params["hold_delay_s"],
                    work_delay=params["work_delay_s"],
                    timeout=params["timeout_s"],
                )
                for i in range(n)
            ]

            t0 = time.perf_counter()
            runner = SimulationRunner(rm, use_detector=True, check_interval=params["check_interval_s"])
            runner.run(specs)
            total_s = time.perf_counter() - t0

            victims = sum(1 for c in runner.results.values() if c == 4)
            success = sum(1 for c in runner.results.values() if c == 0)
            writer.writerow([
                n,
                f"{rm.last_detection_ms:.4f}",
                f"{rm.last_recovery_ms:.4f}",
                f"{total_s:.3f}",
                victims,
                success,
            ])

    print(f"[OK] Saved parameters and raw data to {results_dir}/")


if __name__ == "__main__":
    run_benchmarks()