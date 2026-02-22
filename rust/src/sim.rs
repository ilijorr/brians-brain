use std::fs::File;
use std::io::{BufWriter, Write};
use std::time::Instant;

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use rayon::prelude::*;

const OFF: u8 = 0;
const ON: u8 = 1;
const DYING: u8 = 2;

pub fn init_grid(n: usize, seed: u64) -> Vec<u8> {
    let mut rng = StdRng::seed_from_u64(seed);
    (0..n * n).map(|_| rng.gen_range(0u8..3)).collect()
}

#[inline(always)]
fn apply_rule(cell: u8, neighbors: u8) -> u8 {
    let is_off = (cell == OFF) as u8;
    let is_on  = (cell == ON)  as u8;
    let two    = (neighbors == 2) as u8;
    // OFF->ON = 1·two·1,  ON->DYING = 1·2,  else 0
    is_off * two + is_on * 2
}

fn process_row(above: &[u8], curr: &[u8], below: &[u8], out: &mut [u8]) {
    let n = curr.len();
    if n == 0 {
        return;
    }

    let count = (above[n - 1] == ON) as u8
        + (above[0] == ON) as u8
        + (above[1 % n] == ON) as u8
        + (curr[n - 1] == ON) as u8
        + (curr[1 % n] == ON) as u8
        + (below[n - 1] == ON) as u8
        + (below[0] == ON) as u8
        + (below[1 % n] == ON) as u8;
    out[0] = apply_rule(curr[0], count);

    // The compiler can prove col-1 >= 0 and col+1 < n here, so it strips all
    // bounds checks and auto-vectorises with AVX2 (32 u8/cycle on this CPU).
    for col in 1..n - 1 {
        let count = (above[col - 1] == ON) as u8
            + (above[col] == ON) as u8
            + (above[col + 1] == ON) as u8
            + (curr[col - 1] == ON) as u8
            + (curr[col + 1] == ON) as u8
            + (below[col - 1] == ON) as u8
            + (below[col] == ON) as u8
            + (below[col + 1] == ON) as u8;
        out[col] = apply_rule(curr[col], count);
    }

    if n > 1 {
        let col = n - 1;
        let count = (above[col - 1] == ON) as u8
            + (above[col] == ON) as u8
            + (above[0] == ON) as u8
            + (curr[col - 1] == ON) as u8
            + (curr[0] == ON) as u8
            + (below[col - 1] == ON) as u8
            + (below[col] == ON) as u8
            + (below[0] == ON) as u8;
        out[col] = apply_rule(curr[col], count);
    }
}

fn step_seq(grid: &[u8], new_grid: &mut [u8], n: usize) {
    for row in 0..n {
        let ra = if row == 0 { n - 1 } else { row - 1 };
        let rb = if row == n - 1 { 0 } else { row + 1 };
        process_row(
            &grid[ra * n..(ra + 1) * n],
            &grid[row * n..(row + 1) * n],
            &grid[rb * n..(rb + 1) * n],
            &mut new_grid[row * n..(row + 1) * n],
        );
    }
}

/// `grid` is a shared immutable reference — safe to read from all threads.
/// `new_grid` is split into non-overlapping row chunks — each thread writes
/// to its own region with no synchronisation needed.
fn step_par(grid: &[u8], new_grid: &mut [u8], n: usize) {
    new_grid
        .par_chunks_mut(n)
        .enumerate()
        .for_each(|(row, out_row)| {
            let ra = if row == 0 { n - 1 } else { row - 1 };
            let rb = if row == n - 1 { 0 } else { row + 1 };
            process_row(
                &grid[ra * n..(ra + 1) * n],
                &grid[row * n..(row + 1) * n],
                &grid[rb * n..(rb + 1) * n],
                out_row,
            );
        });
}

pub fn save_bin(path: &str, frames: &[Vec<u8>], n: usize) {
    let file = File::create(path).expect("cannot create output file");
    let mut w = BufWriter::new(file);
    w.write_all(&(n as u64).to_le_bytes()).unwrap();
    w.write_all(&(frames.len() as u64).to_le_bytes()).unwrap();
    for frame in frames {
        w.write_all(frame).unwrap();
    }
}

pub fn run_seq(n: usize, iterations: usize, seed: u64, output: Option<&str>) {
    let mut grid = init_grid(n, seed);
    let mut buf = vec![0u8; n * n];

    let save = output.is_some();
    let mut frames: Vec<Vec<u8>> = if save { vec![grid.clone()] } else { vec![] };

    let t0 = Instant::now();
    for _ in 0..iterations {
        step_seq(&grid, &mut buf, n);
        std::mem::swap(&mut grid, &mut buf);
        if save {
            frames.push(grid.clone());
        }
    }
    println!("{:.6}", t0.elapsed().as_secs_f64());

    if let Some(path) = output {
        save_bin(path, &frames, n);
    }
}

pub fn run_par(n: usize, iterations: usize, seed: u64, threads: usize, output: Option<&str>) {
    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .unwrap();

    let mut grid = init_grid(n, seed);
    let mut buf = vec![0u8; n * n];

    let save = output.is_some();
    let mut frames: Vec<Vec<u8>> = if save { vec![grid.clone()] } else { vec![] };

    let t0 = Instant::now();
    for _ in 0..iterations {
        step_par(&grid, &mut buf, n);
        std::mem::swap(&mut grid, &mut buf);
        if save {
            frames.push(grid.clone());
        }
    }
    println!("{:.6}", t0.elapsed().as_secs_f64());

    if let Some(path) = output {
        save_bin(path, &frames, n);
    }
}
