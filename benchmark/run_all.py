#!/usr/bin/env python3
"""
Brian's Brain scaling benchmark runner.

Run from the repository root:

    python benchmark/run_all.py                 # full run (30 reps, ~4-5h)
    python benchmark/run_all.py --quick         # 5 reps, Rust only (~10 min)
    python benchmark/run_all.py --skip-python   # Rust only, 30 reps (~10 min)
    python benchmark/run_all.py --strong-only   # skip weak scaling
    python benchmark/run_all.py --weak-only     # skip strong scaling

Results → benchmark/results/strong_scaling.csv
          benchmark/results/weak_scaling.csv

CSV columns: impl, mode, p, size, iters, rep, time_s
  impl  : python | rust
  mode  : seq | par
  p     : number of processes / threads
  size  : grid side length N  (grid is N×N)
  iters : simulation steps
  rep   : repetition index (0-based)
  time_s: wall-clock seconds (computation only, no I/O)
"""

import argparse
import csv
import math
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to repo root — run the script from there)
# ---------------------------------------------------------------------------

RESULTS_DIR = Path("benchmark/results")
RUST_BIN    = Path("rust/target/release/brians-brain")
PYTHON_SEQ  = [sys.executable, "python/sequential.py"]
PYTHON_PAR  = [sys.executable, "python/parallel.py"]

# ---------------------------------------------------------------------------
# Experiment parameters (match README spec)
# ---------------------------------------------------------------------------

THREAD_COUNTS  = [1, 2, 4, 8, 16]

STRONG_SIZE    = 5000
STRONG_ITERS   = 500

WEAK_BASE      = 2500   # grid side per process at p=1
WEAK_ITERS     = 200

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_once(cmd: list[str]) -> float:
    """Run *cmd*, return the float seconds printed to stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def weak_size(p: int) -> int:
    """Return N such that N² ≈ p × WEAK_BASE²  (each process gets ~WEAK_BASE² cells)."""
    return round(WEAK_BASE * math.sqrt(p))


def progress(msg: str) -> None:
    print(msg, flush=True)


def estimate_minutes(reps: int, skip_python: bool) -> float:
    """Very rough wall-time estimate in minutes."""
    # Rust: strong (6 configs × 30 reps × ~2s) + weak (5 configs × 30 reps × ~2s)
    rust = (6 + 5) * reps * 2 / 60
    if skip_python:
        return rust
    # Python: strong (6 configs × 30 reps × ~60s) + weak (5 configs × 30 reps × ~40s)
    python = (6 * reps * 60 + 5 * reps * 40) / 60
    return rust + python

# ---------------------------------------------------------------------------
# Strong scaling
# ---------------------------------------------------------------------------

def run_strong(reps: int, skip_python: bool, f_strong) -> None:
    writer = csv.writer(f_strong)

    progress(f"\n{'='*60}")
    progress(f"STRONG SCALING  —  {STRONG_SIZE}×{STRONG_SIZE}, {STRONG_ITERS} iters, {reps} reps")
    progress(f"{'='*60}")

    # ---- Python sequential baseline ----------------------------------------
    if not skip_python:
        progress("\n[Python  seq]")
        for rep in range(reps):
            t = run_once(PYTHON_SEQ + [
                "--size", str(STRONG_SIZE),
                "--iterations", str(STRONG_ITERS),
            ])
            writer.writerow(["python", "seq", 1, STRONG_SIZE, STRONG_ITERS, rep, f"{t:.6f}"])
            f_strong.flush()
            progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

    # ---- Python parallel ----------------------------------------------------
    if not skip_python:
        for p in THREAD_COUNTS:
            progress(f"\n[Python  par  p={p}]")
            for rep in range(reps):
                t = run_once(PYTHON_PAR + [
                    "--size", str(STRONG_SIZE),
                    "--iterations", str(STRONG_ITERS),
                    "--processes", str(p),
                ])
                writer.writerow(["python", "par", p, STRONG_SIZE, STRONG_ITERS, rep, f"{t:.6f}"])
                f_strong.flush()
                progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

    # ---- Rust sequential baseline ------------------------------------------
    progress("\n[Rust    seq]")
    for rep in range(reps):
        t = run_once([str(RUST_BIN),
            "--mode", "seq",
            "--size", str(STRONG_SIZE),
            "--iterations", str(STRONG_ITERS),
        ])
        writer.writerow(["rust", "seq", 1, STRONG_SIZE, STRONG_ITERS, rep, f"{t:.6f}"])
        f_strong.flush()
        progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

    # ---- Rust parallel ------------------------------------------------------
    for p in THREAD_COUNTS:
        progress(f"\n[Rust    par  p={p}]")
        for rep in range(reps):
            t = run_once([str(RUST_BIN),
                "--mode", "par",
                "--size", str(STRONG_SIZE),
                "--iterations", str(STRONG_ITERS),
                "--threads", str(p),
            ])
            writer.writerow(["rust", "par", p, STRONG_SIZE, STRONG_ITERS, rep, f"{t:.6f}"])
            f_strong.flush()
            progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

# ---------------------------------------------------------------------------
# Weak scaling
# ---------------------------------------------------------------------------

def run_weak(reps: int, skip_python: bool, f_weak) -> None:
    writer = csv.writer(f_weak)

    progress(f"\n{'='*60}")
    progress(f"WEAK SCALING  —  base {WEAK_BASE}²/process, {WEAK_ITERS} iters, {reps} reps")
    progress(f"{'='*60}")

    sizes = {p: weak_size(p) for p in THREAD_COUNTS}
    progress("Grid sizes: " + ", ".join(f"p={p}→{n}²" for p, n in sizes.items()))

    # ---- Python parallel ----------------------------------------------------
    if not skip_python:
        for p in THREAD_COUNTS:
            n = sizes[p]
            progress(f"\n[Python  par  p={p}  size={n}]")
            for rep in range(reps):
                t = run_once(PYTHON_PAR + [
                    "--size", str(n),
                    "--iterations", str(WEAK_ITERS),
                    "--processes", str(p),
                ])
                writer.writerow(["python", "par", p, n, WEAK_ITERS, rep, f"{t:.6f}"])
                f_weak.flush()
                progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

    # ---- Rust parallel ------------------------------------------------------
    for p in THREAD_COUNTS:
        n = sizes[p]
        progress(f"\n[Rust    par  p={p}  size={n}]")
        for rep in range(reps):
            t = run_once([str(RUST_BIN),
                "--mode", "par",
                "--size", str(n),
                "--iterations", str(WEAK_ITERS),
                "--threads", str(p),
            ])
            writer.writerow(["rust", "par", p, n, WEAK_ITERS, rep, f"{t:.6f}"])
            f_weak.flush()
            progress(f"  rep {rep+1:2d}/{reps}  {t:.3f}s")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Brian's Brain benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--reps",         type=int, default=30,
                        help="Repetitions per configuration (default: 30)")
    parser.add_argument("--quick",        action="store_true",
                        help="5 reps + skip Python (fast sanity check)")
    parser.add_argument("--skip-python",  action="store_true",
                        help="Skip all Python experiments")
    parser.add_argument("--strong-only",  action="store_true",
                        help="Run only strong scaling")
    parser.add_argument("--weak-only",    action="store_true",
                        help="Run only weak scaling")
    args = parser.parse_args()

    if args.quick:
        args.reps        = 5
        args.skip_python = True

    # Sanity checks
    if not RUST_BIN.exists():
        sys.exit(f"ERROR: {RUST_BIN} not found.\n"
                 f"       Run:  cargo build --release   inside rust/")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    skip_python = args.skip_python
    reps        = args.reps

    progress("Brian's Brain benchmark runner")
    progress(f"  reps        : {reps}")
    progress(f"  skip python : {skip_python}")
    est = estimate_minutes(reps, skip_python)
    progress(f"  estimated   : ~{est:.0f} min")

    total_start = time.perf_counter()

    try:
        if not args.weak_only:
            strong_csv = RESULTS_DIR / "strong_scaling.csv"
            with open(strong_csv, "w", newline="") as f:
                f.write("impl,mode,p,size,iters,rep,time_s\n")
                run_strong(reps, skip_python, f)
            progress(f"\nStrong scaling → {strong_csv}")

        if not args.strong_only:
            weak_csv = RESULTS_DIR / "weak_scaling.csv"
            with open(weak_csv, "w", newline="") as f:
                f.write("impl,mode,p,size,iters,rep,time_s\n")
                run_weak(reps, skip_python, f)
            progress(f"\nWeak scaling   → {weak_csv}")

    except KeyboardInterrupt:
        progress("\n\nInterrupted — partial results saved.")

    elapsed = time.perf_counter() - total_start
    progress(f"\nDone in {elapsed:.1f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
