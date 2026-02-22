#!/usr/bin/env python3

import argparse
import os
import sys
import time

import numpy as np

_BG = {
    0: "\033[40m",    # OFF   -> black
    1: "\033[107m",   # ON    -> bright white
    2: "\033[44m",    # DYING -> blue
}
_RESET  = "\033[0m"
_CLEAR  = "\033[2J\033[H"       # clear screen + cursor home
_HOME   = "\033[H"              # cursor home
_HIDE   = "\033[?25l"           # hide cursor
_SHOW   = "\033[?25h"           # show cursor
_CELL   = "  "                  # two spaces per cell


def _render_frame(frame: np.ndarray,
                  max_rows: int,
                  max_cols: int) -> str:
    H = min(frame.shape[0], max_rows)
    W = min(frame.shape[1], max_cols)
    lines = []
    for row in frame[:H, :W]:
        line = "".join(_BG[int(c)] + _CELL for c in row) + _RESET
        lines.append(line)
    return "\n".join(lines)


def _terminal_capacity() -> tuple[int, int]:
    try:
        term_cols, term_rows = os.get_terminal_size()
    except OSError:
        term_cols, term_rows = 80, 24
    return max(1, term_rows - 2), max(1, term_cols // 2)


def animate(states: np.ndarray,
            delay_ms: int = 50,
            loop: bool = False) -> None:
    max_rows, max_cols = _terminal_capacity()
    n_frames           = len(states)

    sys.stdout.write(_HIDE + _CLEAR)
    sys.stdout.flush()

    try:
        while True:
            for idx, frame in enumerate(states):
                sys.stdout.write(_HOME)
                sys.stdout.write(_render_frame(frame, max_rows, max_cols))
                sys.stdout.write(
                    f"\n\033[K{_RESET}frame {idx + 1}/{n_frames}"
                    f"  grid {frame.shape[0]}x{frame.shape[1]}"
                    f"  (Ctrl-C to quit)"
                )
                sys.stdout.flush()
                time.sleep(delay_ms / 1000.0)
            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(_SHOW + _RESET + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Brian's Brain console visualiser")
    parser.add_argument("input",
                        help="Path to .npy states file (shape: frames x H x W)")
    parser.add_argument("--delay", type=int, default=50,
                        help="Milliseconds between frames (default: 50)")
    parser.add_argument("--loop",  action="store_true",
                        help="Loop the animation until Ctrl-C")
    args = parser.parse_args()

    print(f"Loading {args.input} …", flush=True)
    states = np.load(args.input)

    if states.ndim != 3:
        sys.exit(f"Expected 3-D array (frames x H x W), got shape {states.shape}")

    print(f"  {len(states)} frames, grid {states.shape[1]}x{states.shape[2]}")
    time.sleep(0.4)

    animate(states, delay_ms=args.delay, loop=args.loop)


if __name__ == "__main__":
    main()
