from __future__ import annotations

import csv
from pathlib import Path
import matplotlib.pyplot as plt


def main() -> None:
    results_dir = Path("experiments/results")
    csv_path = results_dir / "experimental_data.csv"
    if not csv_path.exists():
        raise FileNotFoundError("Run `python -m experiments.run_benchmarks` first.")

    nb_proc, dfs_ms, total_s = [], [], []
    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nb_proc.append(int(row["nb_processus"]))
            dfs_ms.append(float(row["temps_detection_dfs_ms"]))
            total_s.append(float(row["temps_total_simulation_s"]))

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.set_xlabel("Concurrent processes in cycle (N)")
    ax1.set_ylabel("DFS detection latency (ms)", color="#1f77b4")
    ax1.plot(nb_proc, dfs_ms, marker="o", color="#1f77b4")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    ax2.set_ylabel("Total simulation time (s)", color="#d62728")
    ax2.plot(nb_proc, total_s, marker="s", linestyle="--", color="#d62728")

    plt.title("DFS Detection Latency vs. Cycle Size")
    fig.tight_layout()
    fig.savefig(results_dir / "performance_dfs.png", dpi=300)
    plt.close(fig)
    print(f"[OK] Chart saved to {results_dir / 'performance_dfs.png'}")


if __name__ == "__main__":
    main()