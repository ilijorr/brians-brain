#!/usr/bin/env python3

import argparse
import time
from multiprocessing import Process, Queue

import numpy as np

OFF, ON, DYING = np.uint8(0), np.uint8(1), np.uint8(2)


def _count_on_neighbors_padded(padded: np.ndarray) -> np.ndarray:
    on = (padded == ON).astype(np.uint8)
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


def _step_chunk(chunk: np.ndarray,
                top_ghost: np.ndarray,
                bot_ghost: np.ndarray) -> np.ndarray:
    padded          = np.vstack([top_ghost[np.newaxis], chunk, bot_ghost[np.newaxis]])
    neighbor_counts = _count_on_neighbors_padded(padded)[1:-1]

    new_chunk = np.zeros_like(chunk)
    new_chunk[(chunk == OFF) & (neighbor_counts == 2)] = ON
    new_chunk[chunk == ON]                             = DYING
    return new_chunk


def _worker(rank: int,
            P: int,
            chunk: np.ndarray,
            iterations: int,
            top_ghost_for: list,
            bot_ghost_for: list,
            result_q: Queue,
            save_states: bool) -> None:

    states = [chunk.copy()] if save_states else None

    for _ in range(iterations):
        # send boundary rows to neighbours
        top_ghost_for[(rank + 1) % P].put(chunk[-1].copy())
        bot_ghost_for[(rank - 1) % P].put(chunk[0].copy())

        top_ghost = top_ghost_for[rank].get()
        bot_ghost = bot_ghost_for[rank].get()

        chunk = _step_chunk(chunk, top_ghost, bot_ghost)

        if save_states:
            states.append(chunk.copy())

    result_q.put((rank, states))


def main() -> None:
    parser = argparse.ArgumentParser(description="Brian's Brain parallel simulation")
    parser.add_argument("--size",       type=int, default=100,  help="Grid size N (NxN)")
    parser.add_argument("--iterations", type=int, default=100,  help="Number of steps")
    parser.add_argument("--processes",  type=int, default=4,    help="Number of worker processes")
    parser.add_argument("--output",     type=str, default=None, help="Save all frames to .npy")
    parser.add_argument("--seed",       type=int, default=42,   help="Random seed")
    args = parser.parse_args()

    P    = args.processes
    rng  = np.random.default_rng(args.seed)
    grid = rng.integers(0, 3, size=(args.size, args.size), dtype=np.uint8)

    chunks = np.array_split(grid, P, axis=0)

    save_states = args.output is not None

    top_ghost_for = [Queue() for _ in range(P)]
    bot_ghost_for = [Queue() for _ in range(P)]
    result_q      = Queue()

    t0 = time.perf_counter()

    workers = []
    for rank in range(P):
        p = Process(
            target=_worker,
            args=(rank, P, chunks[rank], args.iterations,
                  top_ghost_for, bot_ghost_for, result_q, save_states),
        )
        p.start()
        workers.append(p)

    results = {}
    for _ in range(P):
        rank, states = result_q.get()
        results[rank] = states

    for p in workers:
        p.join()

    elapsed = time.perf_counter() - t0
    print(f"{elapsed:.6f}")

    if save_states:
        n_frames  = args.iterations + 1
        all_states = [
            np.vstack([results[r][i] for r in range(P)])
            for i in range(n_frames)
        ]
        np.save(args.output, np.array(all_states, dtype=np.uint8))


if __name__ == "__main__":
    main()
