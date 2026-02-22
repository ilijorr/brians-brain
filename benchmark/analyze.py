#!/usr/bin/env python3
"""
Brian's Brain - Benchmark analysis and plot generator.

Reads:
  benchmark/results/strong_scaling.csv
  benchmark/results/weak_scaling.csv

Outputs:
  benchmark/plots/strong_python.png
  benchmark/plots/strong_rust.png
  benchmark/plots/weak_python.png
  benchmark/plots/weak_rust.png
  benchmark/results/table_strong_python.csv
  benchmark/results/table_strong_rust.csv
  benchmark/results/table_weak_python.csv
  benchmark/results/table_weak_rust.csv

Run from the repository root:
    python benchmark/analyze.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar

RESULTS_DIR   = Path("benchmark/results")
PLOTS_DIR     = Path("benchmark/plots")
THREAD_COUNTS = [1, 2, 4, 8, 16]

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def amdahl(p: np.ndarray, f: float) -> np.ndarray:
    return 1.0 / (f + (1.0 - f) / p)


def gustafson(p: np.ndarray, f: float) -> np.ndarray:
    return p - f * (p - 1.0)


def fit_law(ps: np.ndarray, speedups: np.ndarray, law_fn) -> float:
    def mse(f):
        return np.mean((law_fn(ps, f) - speedups) ** 2)
    return minimize_scalar(mse, bounds=(1e-9, 1.0 - 1e-9), method="bounded").x


def count_outliers(values: np.ndarray, k: float = 2.0) -> int:
    """Number of values more than k standard deviations from the mean."""
    if len(values) < 3:
        return 0
    return int(np.sum(np.abs(values - values.mean()) > k * values.std()))


def analyze_strong(df: pd.DataFrame) -> None:
    print("\n" + "=" * 65)
    print("STRONG SCALING ANALYSIS")
    print("=" * 65)

    for impl in ["python", "rust"]:
        sub = df[df["impl"] == impl]
        if sub.empty:
            print(f"\n  [{impl}] No data — skipping.")
            continue

        seq = sub[sub["mode"] == "seq"]["time_s"]
        par = sub[sub["mode"] == "par"]
        if seq.empty or par.empty:
            print(f"\n  [{impl}] Missing seq or par data — skipping.")
            continue

        T_seq      = seq.mean()
        T_seq_std  = seq.std()

        rows, ps, speedups, errs = [], [], [], []

        for p in sorted(par["p"].unique()):
            times = par[par["p"] == p]["time_s"].values
            mu    = times.mean()
            sigma = times.std()
            S     = T_seq / mu
            # Error propagation: σ_S/S ≈ sqrt((σ_Tseq/T_seq)² + (σ_T/T)²)
            S_err = S * np.sqrt((T_seq_std / T_seq) ** 2 + (sigma / mu) ** 2)

            rows.append({
                "cores":        int(p),
                "mean_time_s":  round(mu, 4),
                "std_s":        round(sigma, 4),
                "speedup":      round(S, 4),
                "efficiency_%": round(100 * S / p, 1),
                "outliers":     count_outliers(times),
            })
            ps.append(p)
            speedups.append(S)
            errs.append(S_err)

        ps       = np.array(ps, dtype=float)
        speedups = np.array(speedups)
        errs     = np.array(errs)

        f_seq    = fit_law(ps, speedups, amdahl)
        S_max    = 1.0 / f_seq if f_seq > 0 else float("inf")

        table = pd.DataFrame(rows)

        # --- print ---
        print(f"\n  [{impl.upper()}]")
        print(f"  Sequential baseline : {T_seq:.4f}s ± {T_seq_std:.4f}s")
        print(f"  Amdahl fit          : f_seq = {f_seq*100:.1f}%  "
              f"f_par = {(1-f_seq)*100:.1f}%")
        print(f"  Theoretical max S   : {S_max:.2f}×  (infinite cores)")
        print()
        print(table.to_string(index=False))

        # --- save table ---
        csv_path = RESULTS_DIR / f"table_strong_{impl}.csv"
        table.to_csv(csv_path, index=False)
        print(f"\n  Table saved → {csv_path}")

        # --- plot ---
        p_range       = np.linspace(1, max(ps), 300)
        ideal_line    = p_range
        amdahl_curve  = amdahl(p_range, f_seq)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(p_range, ideal_line,   "k--", lw=1.2, label="Ideal (linear)")
        ax.plot(p_range, amdahl_curve, "r-",  lw=2.0,
                label=f"Amdahl  (f_seq = {f_seq*100:.1f}%)")
        ax.errorbar(ps, speedups, yerr=errs,
                    fmt="bo-", ms=6, capsize=4, lw=2, label="Measured")

        ax.set_xlabel("Number of cores / threads")
        ax.set_ylabel("Speedup  S(p) = T(1) / T(p)")
        ax.set_title(f"Strong Scaling — {impl.capitalize()}")
        ax.set_xticks(THREAD_COUNTS)
        ax.set_xlim(0.5, max(ps) + 0.5)
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        plot_path = PLOTS_DIR / f"strong_{impl}.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"  Plot  saved → {plot_path}")

# ---------------------------------------------------------------------------
# Weak scaling
# ---------------------------------------------------------------------------

def analyze_weak(df: pd.DataFrame) -> None:
    print("\n" + "=" * 65)
    print("WEAK SCALING ANALYSIS")
    print("=" * 65)

    for impl in ["python", "rust"]:
        sub = df[(df["impl"] == impl) & (df["mode"] == "par")]
        if sub.empty:
            print(f"\n  [{impl}] No data — skipping.")
            continue

        base = sub[sub["p"] == 1]["time_s"]
        if base.empty:
            print(f"\n  [{impl}] No p=1 baseline — skipping.")
            continue

        T_base      = base.mean()
        T_base_std  = base.std()

        rows, ps, speedups, errs = [], [], [], []

        for p in sorted(sub["p"].unique()):
            times = sub[sub["p"] == p]["time_s"].values
            size  = int(sub[sub["p"] == p]["size"].iloc[0])
            mu    = times.mean()
            sigma = times.std()
            # Scaled speedup: S(p) = p * T_base / T(p)
            S     = p * T_base / mu
            S_err = S * np.sqrt((T_base_std / T_base) ** 2 + (sigma / mu) ** 2)

            rows.append({
                "cores":          int(p),
                "grid":           f"{size}×{size}",
                "mean_time_s":    round(mu, 4),
                "std_s":          round(sigma, 4),
                "scaled_speedup": round(S, 4),
                "efficiency_%":   round(100 * S / p, 1),
                "outliers":       count_outliers(times),
            })
            ps.append(p)
            speedups.append(S)
            errs.append(S_err)

        ps       = np.array(ps, dtype=float)
        speedups = np.array(speedups)
        errs     = np.array(errs)

        f_seq = fit_law(ps, speedups, gustafson)

        table = pd.DataFrame(rows)

        # --- print ---
        print(f"\n  [{impl.upper()}]")
        print(f"  Baseline (p=1)    : {T_base:.4f}s ± {T_base_std:.4f}s")
        print(f"  Gustafson fit     : f_seq = {f_seq*100:.1f}%  "
              f"f_par = {(1-f_seq)*100:.1f}%")
        print()
        print(table.to_string(index=False))

        # --- save table ---
        csv_path = RESULTS_DIR / f"table_weak_{impl}.csv"
        table.to_csv(csv_path, index=False)
        print(f"\n  Table saved → {csv_path}")

        # --- plot ---
        p_range          = np.linspace(1, max(ps), 300)
        ideal_line       = p_range
        gustafson_curve  = gustafson(p_range, f_seq)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(p_range, ideal_line,      "k--", lw=1.2, label="Ideal (linear)")
        ax.plot(p_range, gustafson_curve, "r-",  lw=2.0,
                label=f"Gustafson  (f_seq = {f_seq*100:.1f}%)")
        ax.errorbar(ps, speedups, yerr=errs,
                    fmt="bo-", ms=6, capsize=4, lw=2, label="Measured")

        ax.set_xlabel("Number of cores / threads")
        ax.set_ylabel("Scaled Speedup  S(p) = p · T(1) / T(p)")
        ax.set_title(f"Weak Scaling — {impl.capitalize()}")
        ax.set_xticks(THREAD_COUNTS)
        ax.set_xlim(0.5, max(ps) + 0.5)
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        plot_path = PLOTS_DIR / f"weak_{impl}.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"  Plot  saved → {plot_path}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    strong_csv = RESULTS_DIR / "strong_scaling.csv"
    weak_csv   = RESULTS_DIR / "weak_scaling.csv"

    if not strong_csv.exists() and not weak_csv.exists():
        sys.exit(f"No results found in {RESULTS_DIR}/\n"
                 f"Run:  python benchmark/run_all.py  first.")

    if strong_csv.exists():
        print(f"Loading {strong_csv} ...")
        analyze_strong(pd.read_csv(strong_csv))
    else:
        print(f"Skipping strong scaling (no file found).")

    if weak_csv.exists():
        print(f"\nLoading {weak_csv} ...")
        analyze_weak(pd.read_csv(weak_csv))
    else:
        print(f"Skipping weak scaling (no file found).")

    print(f"\nDone.  Plots → {PLOTS_DIR}/")


if __name__ == "__main__":
    main()
