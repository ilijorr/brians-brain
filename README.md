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

## Vizualizacija (10 poena)

**Rust + Plotters biblioteka**
- Učitaj stanja iz fajlova
- Generiši frame-ove:
  - Off (0): crna
  - On (1): bela
  - Dying (2): plava
- Izvoz: PNG sekvenca ili GIF

---

## Očekivani Rezultati

**Speedup:**
- Python paralelni: ~3-6× (8 jezgara, GIL limit)
- Rust paralelni: ~7-8× (8 jezgara, pravi paralelizam)

---

Ilija Jordanovski SV 73/2022
