# Brian's Brain - NTP Projekat Specifikacija

## Problem

**Brian's Brain** - trostani ćelularni automat (2D mreža)

**Stanja:** Off (0), On (1), Dying (2)

**Pravila:**
- Off → On: ako ima tačno 2 On suseda
- On → Dying: uvek
- Dying → Off: uvek

**Iterativni proces:** Svaki korak generiše novo stanje cele mreže

---

## Python Implementacija

### Sekvencijalna
- 2D numpy mreža (N×N)
- Iterativno računanje novih stanja
- Izlaz: `states_seq_python.npy` (sva stanja po iteracijama)

### Paralelna (multiprocessing)
- Podela mreže na horizontalne blokove (P procesa)
- Ghost rows komunikacija između procesa
- Izlaz: `states_par_python.npy`

---

## Rust Implementacija

### Sekvencijalna
- `Vec<u8>` za čuvanje stanja
- Izlaz: `states_seq_rust.bin`

### Paralelna (threads)
- Rayon biblioteka za paralelizaciju
- Thread-safe podela mreže
- Izlaz: `states_par_rust.bin`

---

## Eksperimenti Skaliranja

### Jako skaliranje
**Setup:**
- Fiksna mreža: 5000×5000
- Iteracije: 500
- Procesi/threadovi: 1, 2, 4, 8, 16
- Ponavljanja: 30×

**Merenje:**
- Speedup: S(p) = T(1) / T(p)
- Efikasnost: E(p) = S(p) / p
- Amdahlov zakon: S(p) = 1 / (f_seq + (1-f_seq)/p)

### Slabo skaliranje (Weak Scaling)
**Setup:**
- Bazna veličina: 2500×2500 po procesu
- Skaliranje: 1p→2500×2500, 2p→2500×5000, 4p→2500×10000...
- Iteracije: 200
- Ponavljanja: 30×

**Merenje:**
- Scaled speedup: S(p) = p × T(1) / T(p)
- Gustafsonov zakon: S(p) = p - f_seq × (p - 1)

---

## Vizualizacija

Konzolna animacija u terminalu. Boje: Off → crna, On → bela, Dying → plava.

**Python:**
```bash
python python/sequential.py --size 100 --iterations 200 --output states.npy
python python/visualize.py states.npy --delay 80 --loop
```

**Rust:**
```bash
cd rust && cargo build --release
./target/release/brians-brain --mode seq --size 100 --iterations 200 --output states.bin
./target/release/brians-brain --mode viz --input states.bin --delay 80 --loop
```

---

## Očekivani Rezultati

**Speedup:**
- Python paralelni: ~3-6× (8 jezgara, GIL limit)
- Rust paralelni: ~7-8× (8 jezgara, pravi paralelizam)

---

Ilija Jordanovski SV 73/2022

---

## Korišćenje

### Python

```bash
# Sekvencijalna simulacija
python python/sequential.py [--size N] [--iterations N] [--output FILE.npy] [--seed N]

# Paralelna simulacija
python python/parallel.py [--size N] [--iterations N] [--processes N] [--output FILE.npy] [--seed N]

# Vizualizacija
python python/visualize.py FILE.npy [--delay MS] [--loop]
```

Podrazumevane vrednosti: `--size 100`, `--iterations 100`, `--seed 42`, `--processes 4`, `--delay 50`

### Rust

```bash
cd rust && cargo build --release

# Sekvencijalna simulacija
./target/release/brians-brain --mode seq [--size N] [--iterations N] [--seed N] [--output FILE.bin]

# Paralelna simulacija
./target/release/brians-brain --mode par [--size N] [--iterations N] [--seed N] [--threads N] [--output FILE.bin]

# Vizualizacija
./target/release/brians-brain --mode viz --input FILE.bin [--delay MS] [--loop]
```

Podrazumevane vrednosti: `--size 100`, `--iterations 100`, `--seed 42`, `--threads 4`, `--delay 50`  
Napomena: `--input` je obavezan za `--mode viz`.

### Benchmarkovi

```bash
python benchmark/run_all.py [--reps N] [--quick] [--skip-python] [--strong-only] [--weak-only]
```

- `--reps N` — broj ponavljanja (podrazumevano: 30)
- `--quick` — kratak test
- `--skip-python` — samo Rust benchmark
- `--strong-only` / `--weak-only` — samo jako / slabo skaliranje

Rezultati se čuvaju u `benchmark/results/`, grafici u `benchmark/plots/`.
