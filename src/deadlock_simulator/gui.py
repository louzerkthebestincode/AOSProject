from __future__ import annotations

import csv
import logging
from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .core.resource_manager import ResourceManager
from .logging_config import LOG_FORMAT, configure_logging
from .scenarios import (
    run_deadlock,
    run_errors,
    run_philosophers,
    run_prevention,
    run_safe,
)


class TkLogHandler(logging.Handler):
    """Streams simulator logs safely to the Tkinter ScrolledText widget."""

    def __init__(self, widget: scrolledtext.ScrolledText) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        level = record.levelname

        def _append() -> None:
            self.widget.configure(state="normal")
            self.widget.insert(tk.END, msg + "\n", level)
            self.widget.see(tk.END)
            self.widget.configure(state="disabled")

        self.widget.after(0, _append)


class BasicDeadlockGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Deadlock Simulator — AOS Project")
        self.root.geometry("1120x680")
        self.root.configure(bg="#1e1e2e")

        self.active_rm: ResourceManager | None = None
        self.is_running = False

        # Capture the active ResourceManager whenever a scenario starts
        orig_init = ResourceManager.__init__
        gui_ref = self

        def _hooked_init(rm_self: ResourceManager, *args, **kwargs) -> None:
            orig_init(rm_self, *args, **kwargs)
            gui_ref.active_rm = rm_self

        ResourceManager.__init__ = _hooked_init  # type: ignore[method-assign]

        self._build_ui()
        self._setup_logging()
        self._poll_state()

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self.root, bg="#11111b", pady=10)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="DEADLOCK SIMULATOR & DFS DETECTOR",
            fg="#cdd6f4",
            bg="#11111b",
            font=("Segoe UI", 13, "bold"),
        ).pack()

        body = tk.Frame(self.root, bg="#1e1e2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel: controls + live state
        left = tk.Frame(body, bg="#181825", width=330, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(
            left,
            text="SCENARIOS",
            fg="#89b4fa",
            bg="#181825",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        scenarios = [
            ("1. Safe (No Deadlock)", run_safe, "#a6e3a1"),
            ("2. Deadlock (2 Processes)", run_deadlock, "#fab387"),
            ("3. Dining Philosophers (5)", run_philosophers, "#f38ba8"),
            ("4. Total Order Prevention", run_prevention, "#89dceb"),
            ("5. Controlled Errors", run_errors, "#cba6f7"),
        ]

        self.scenario_buttons: list[tk.Button] = []
        for label, fn, color in scenarios:
            btn = tk.Button(
                left,
                text=label,
                bg=color,
                fg="#11111b",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                pady=6,
                command=lambda f=fn, name=label: self.start_scenario(f, name),
            )
            btn.pack(fill=tk.X, pady=3)
            self.scenario_buttons.append(btn)

        # Utility buttons
        tk.Frame(left, bg="#313244", height=2).pack(fill=tk.X, pady=10)

        self.stop_btn = tk.Button(
            left,
            text="Stop Current Simulation",
            bg="#f38ba8",
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            pady=5,
            state="disabled",
            command=self.stop_simulation,
        )
        self.stop_btn.pack(fill=tk.X, pady=2)

        tk.Button(
            left,
            text="View Benchmark CSV",
            bg="#45475a",
            fg="#cdd6f4",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            pady=5,
            command=self.show_csv,
        ).pack(fill=tk.X, pady=2)

        tk.Button(
            left,
            text="Clear Logs",
            bg="#313244",
            fg="#cdd6f4",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            pady=5,
            command=self.clear_logs,
        ).pack(fill=tk.X, pady=2)

        # Live state box
        tk.Frame(left, bg="#313244", height=2).pack(fill=tk.X, pady=10)
        tk.Label(
            left,
            text="LIVE SYSTEM STATE",
            fg="#f9e2af",
            bg="#181825",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        self.status_lbl = tk.Label(
            left,
            text="Status: Ready",
            fg="#a6e3a1",
            bg="#181825",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_lbl.pack(anchor="w", pady=(3, 5))

        self.state_box = tk.Text(
            left,
            bg="#11111b",
            fg="#cdd6f4",
            font=("Consolas", 9),
            state="disabled",
            relief=tk.FLAT,
        )
        self.state_box.pack(fill=tk.BOTH, expand=True)

        # Right panel: live logs
        right = tk.Frame(body, bg="#181825", padx=10, pady=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            right,
            text="EXECUTION LOGS (logs/simulation.log)",
            fg="#89b4fa",
            bg="#181825",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.log_text = scrolledtext.ScrolledText(
            right,
            bg="#11111b",
            fg="#cdd6f4",
            font=("Consolas", 9),
            state="disabled",
            wrap=tk.NONE,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO", foreground="#a6e3a1")
        self.log_text.tag_config("WARNING", foreground="#f9e2af")
        self.log_text.tag_config("ERROR", foreground="#f38ba8")
        self.log_text.tag_config("CRITICAL", foreground="#11111b", background="#f38ba8")

    def _setup_logging(self) -> None:
        logger = configure_logging("logs/simulation.log")
        gui_handler = TkLogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(gui_handler)

    def _poll_state(self) -> None:
        rm = self.active_rm
        if rm is not None and rm.lock.acquire(blocking=False):
            try:
                allocs = {pid: dict(res) for pid, res in rm.allocations.items()}
                waits = {res: list(q) for res, q in rm.wait_queues.items() if q}
                aborted = sorted(rm.aborted)
                cycles = rm.deadlocks_detected
                dfs_ms = rm.last_detection_ms
            finally:
                rm.lock.release()

            lines = ["--- ALLOCATIONS ---"]
            if allocs:
                for pid, held in sorted(allocs.items()):
                    items = ", ".join(f"{r}({c})" for r, c in sorted(held.items()))
                    lines.append(f"  {pid}: {items}")
            else:
                lines.append("  (none)")

            lines.append("\n--- WAIT QUEUES (FIFO) ---")
            if waits:
                for res, q in sorted(waits.items()):
                    lines.append(f"  {res}: {q}")
            else:
                lines.append("  (none)")

            lines.append("\n--- DFS DETECTOR ---")
            lines.append(f"  Cycles detected: {cycles}")
            lines.append(f"  Last DFS time:   {dfs_ms:.4f} ms")
            lines.append(f"  Victims:         {aborted if aborted else 'none'}")

            self.state_box.configure(state="normal")
            self.state_box.delete("1.0", tk.END)
            self.state_box.insert(tk.END, "\n".join(lines))
            self.state_box.configure(state="disabled")

        self.root.after(150, self._poll_state)

    def start_scenario(self, fn, label: str) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.status_lbl.config(text=f"Status: Running {label}", fg="#f9e2af")
        for btn in self.scenario_buttons:
            btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        def _run() -> None:
            try:
                fn()
            finally:
                self.root.after(0, self._on_done)

        threading.Thread(target=_run, daemon=True).start()

    def stop_simulation(self) -> None:
        if self.active_rm is not None:
            self.active_rm.trigger_shutdown()
            self.status_lbl.config(text="Status: Stopping...", fg="#f38ba8")

    def _on_done(self) -> None:
        self.is_running = False
        self.status_lbl.config(text="Status: Finished cleanly", fg="#a6e3a1")
        for btn in self.scenario_buttons:
            btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def clear_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def show_csv(self) -> None:
        csv_path = Path("experiments/results/experimental_data.csv")
        if not csv_path.exists():
            messagebox.showinfo(
                "No CSV Found",
                "Run `python -m experiments.run_benchmarks` first to generate experimental_data.csv.",
            )
            return

        with csv_path.open("r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if not rows:
            return

        win = tk.Toplevel(self.root)
        win.title("Benchmark Results (experimental_data.csv)")
        win.geometry("760x260")

        headers = rows[0]
        tree = ttk.Treeview(win, columns=headers, show="headings")
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, width=120, anchor="center")
        for row in rows[1:]:
            tree.insert("", tk.END, values=row)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


def main() -> None:
    root = tk.Tk()
    BasicDeadlockGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()