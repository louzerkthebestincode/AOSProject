"""Exécute un benchmark reproductible du détecteur de cycles."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from deadlock_simulator.core.detector import find_cycles  # noqa: E402


def make_chain_graph(size: int, with_cycle: bool) -> dict[str, set[str]]:
    """Construit un graphe déterministe P0 -> P1 -> ... -> Pn."""
    nodes = [f"P{i:04d}" for i in range(size)]
    graph = {node: set() for node in nodes}
    for index in range(size - 1):
        graph[nodes[index]].add(nodes[index + 1])
    if with_cycle and size > 1:
        graph[nodes[-1]].add(nodes[0])
    return graph


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    sizes = config.get("graph_sizes")
    if not isinstance(sizes, list) or not sizes or any(
        not isinstance(size, int) or isinstance(size, bool) or size < 2 for size in sizes
    ):
        raise ValueError("graph_sizes doit contenir des entiers supérieurs ou égaux à 2")
    if len(set(sizes)) != len(sizes):
        raise ValueError("graph_sizes ne doit pas contenir de doublons")
    repetitions = config.get("repetitions")
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        raise ValueError("repetitions doit être supérieur ou égal à 1")
    allowed = {"acyclic_chain", "single_cycle_chain"}
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios or not set(scenarios).issubset(allowed):
        raise ValueError(f"scenarios doit utiliser uniquement: {sorted(allowed)}")
    if len(set(scenarios)) != len(scenarios):
        raise ValueError("scenarios ne doit pas contenir de doublons")
    return config


def run_benchmark(
    config: dict[str, Any], run_id: str, config_sha256: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, int], list[int]] = defaultdict(list)
    detected_counts: dict[tuple[str, int], list[int]] = defaultdict(list)
    environment = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    for scenario in config["scenarios"]:
        with_cycle = scenario == "single_cycle_chain"
        for size in config["graph_sizes"]:
            graph = make_chain_graph(size, with_cycle)
            edge_count = sum(len(neighbors) for neighbors in graph.values())
            for repetition in range(1, config["repetitions"] + 1):
                started_ns = time.perf_counter_ns()
                cycles = find_cycles(graph)
                elapsed_ns = time.perf_counter_ns() - started_ns
                expected_cycles = int(with_cycle)
                if len(cycles) != expected_cycles:
                    raise RuntimeError(
                        f"Résultat inattendu pour {scenario}, taille {size}: "
                        f"{len(cycles)} cycle(s), {expected_cycles} attendu(s)"
                    )
                grouped[(scenario, size)].append(elapsed_ns)
                detected_counts[(scenario, size)].append(len(cycles))
                raw_rows.append(
                    {
                        "run_id": run_id,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "experiment": config["experiment"],
                        "config_sha256": config_sha256,
                        "repetitions_configured": config["repetitions"],
                        "scenario": scenario,
                        "graph_size_nodes": size,
                        "graph_size_edges": edge_count,
                        "repetition": repetition,
                        "elapsed_ns": elapsed_ns,
                        "cycles_detected": len(cycles),
                        **environment,
                    }
                )

    summary_rows = []
    for (scenario, size), timings in sorted(grouped.items()):
        summary_rows.append(
            {
                "run_id": run_id,
                "scenario": scenario,
                "graph_size_nodes": size,
                "repetitions": len(timings),
                "mean_elapsed_ns": round(statistics.mean(timings), 2),
                "median_elapsed_ns": round(statistics.median(timings), 2),
                "min_elapsed_ns": min(timings),
                "max_elapsed_ns": max(timings),
                "cycles_detected": detected_counts[(scenario, size)][0],
                "cycles_expected": int(scenario == "single_cycle_chain"),
            }
        )
    return raw_rows, summary_rows


def write_results(
    raw_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], results_dir: Path
) -> tuple[Path, Path, Path]:
    raw_dir = results_dir / "raw"
    tables_dir = results_dir / "tables"
    figures_dir = results_dir / "figures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    run_id = raw_rows[0]["run_id"]
    raw_path = raw_dir / f"{run_id}_raw.jsonl"
    summary_path = tables_dir / f"{run_id}_summary.csv"
    figure_path = figures_dir / f"{run_id}_detection_time.svg"
    existing = [path for path in (raw_path, summary_path, figure_path) if path.exists()]
    if existing:
        raise FileExistsError(f"Identifiant d'exécution déjà utilisé: {run_id}")
    with raw_path.open("w", encoding="utf-8", newline="") as file:
        for row in raw_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with summary_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    write_svg_chart(summary_rows, figure_path)
    return raw_path, summary_path, figure_path


def write_svg_chart(summary_rows: list[dict[str, Any]], figure_path: Path) -> None:
    """Produit un graphique SVG sans dépendance externe."""
    width, height = 800, 480
    left, right, top, bottom = 90, 30, 55, 85
    plot_width, plot_height = width - left - right, height - top - bottom
    sizes = sorted({int(row["graph_size_nodes"]) for row in summary_rows})
    max_value = max(float(row["mean_elapsed_ns"]) for row in summary_rows) or 1.0
    colors = {"acyclic_chain": "#2563eb", "single_cycle_chain": "#dc2626"}
    labels = {"acyclic_chain": "Chaîne sans cycle", "single_cycle_chain": "Chaîne avec cycle"}

    def x_position(size: int) -> float:
        if len(sizes) == 1:
            return left + plot_width / 2
        return left + sizes.index(size) * plot_width / (len(sizes) - 1)

    def y_position(value: float) -> float:
        return top + plot_height * (1 - value / max_value)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="400" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Temps moyen de détection des cycles</text>',
    ]
    for tick in range(6):
        value = max_value * tick / 5
        y = y_position(value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{value/1_000_000:.3f}</text>')
    for size in sizes:
        x = x_position(size)
        parts.append(f'<text x="{x:.1f}" y="{height-bottom+22}" text-anchor="middle" font-family="sans-serif" font-size="12">{size}</text>')
    parts.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>',
            f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>',
            f'<text x="{left + plot_width/2:.1f}" y="{height-20}" text-anchor="middle" font-family="sans-serif" font-size="13">Nombre de processus</text>',
            f'<text x="22" y="{top + plot_height/2:.1f}" transform="rotate(-90 22 {top + plot_height/2:.1f})" text-anchor="middle" font-family="sans-serif" font-size="13">Temps moyen (ms)</text>',
        ]
    )

    for series_index, scenario in enumerate(colors):
        rows = sorted(
            (row for row in summary_rows if row["scenario"] == scenario),
            key=lambda row: int(row["graph_size_nodes"]),
        )
        points = [
            (x_position(int(row["graph_size_nodes"])), y_position(float(row["mean_elapsed_ns"])))
            for row in rows
        ]
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(f'<polyline points="{point_text}" fill="none" stroke="{colors[scenario]}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[scenario]}"/>')
        legend_x = left + 25 + series_index * 250
        parts.append(f'<line x1="{legend_x}" y1="{height-54}" x2="{legend_x+28}" y2="{height-54}" stroke="{colors[scenario]}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x+36}" y="{height-50}" font-family="sans-serif" font-size="12">{labels[scenario]}</text>')

    parts.append('</svg>')
    figure_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "configurations" / "detector_benchmark.json",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "results",
    )
    parser.add_argument("--run-id", help="Identifiant du lancement; généré automatiquement par défaut")
    args = parser.parse_args()

    config = load_config(args.config)
    config_sha256 = hashlib.sha256(args.config.read_bytes()).hexdigest()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("detector_%Y%m%dT%H%M%S_%fZ")
    raw_rows, summary_rows = run_benchmark(config, run_id, config_sha256)
    raw_path, summary_path, figure_path = write_results(raw_rows, summary_rows, args.results_dir)
    print(f"Échantillons bruts: {raw_path}")
    print(f"Résumé: {summary_path}")
    print(f"Graphique: {figure_path}")
    print(f"Nombre de mesures: {len(raw_rows)}")


if __name__ == "__main__":
    main()
