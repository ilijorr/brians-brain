#!/usr/bin/env python3

import argparse
import time

import numpy as np

OFF, ON, DYING = np.uint8(0), np.uint8(1), np.uint8(2)


def count_on_neighbors(grid: np.ndarray) -> np.ndarray:
    on = (grid == ON).astype(np.uint8)
    return (
        np.roll(on, (-1, -1), axis=(0, 1))
        + np.roll(on, (-1,  0), axis=(0, 1))
        + np.roll(on, (-1,  1), axis=(0, 1))
        + np.roll(on, ( 0, -1), axis=(0, 1))
        + np.roll(on, ( 0,  1), axis=(0, 1))
        + np.roll(on, ( 1, -1), axis=(0, 1))
        + np.roll(on, ( 1,  0), axis=(0, 1))
        + np.roll(on, ( 1,  1), axis=(0, 1))
    )


def step(grid: np.ndarray) -> np.ndarray:
    neighbors = count_on_neighbors(grid)
    new_grid = np.zeros_like(grid)
    new_grid[(grid == OFF) & (neighbors == 2)] = ON
    new_grid[grid == ON] = DYING
    return new_grid


def main() -> None:
    parser = argparse.ArgumentParser(description="Brian's Brain sequential simulation")
    parser.add_argument("--size",       type=int,   default=100,  help="Grid size N (NxN)")
    parser.add_argument("--iterations", type=int,   default=100,  help="Number of steps")
    parser.add_argument("--output",     type=str,   default=None, help="Save all frames to .npy")
    parser.add_argument("--seed",       type=int,   default=42,   help="Random seed")
    args = parser.parse_args()

    rng  = np.random.default_rng(args.seed)
    grid = rng.integers(0, 3, size=(args.size, args.size), dtype=np.uint8)

    save   = args.output is not None
    states = [grid.copy()] if save else None

    t0 = time.perf_counter()
    for _ in range(args.iterations):
        grid = step(grid)
        if save:
            states.append(grid.copy())
    elapsed = time.perf_counter() - t0

    print(f"{elapsed:.6f}")

    if save:
        np.save(args.output, np.array(states, dtype=np.uint8))


if __name__ == "__main__":
    main()
