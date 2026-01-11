# Brian's Brain - HPC Projekat Specifikacija

## Problem

**Brian's Brain** - trostani ćelularni automat (2D mreža)

**Stanja:** Off (0), On (1), Dying (2)

**Pravila:**
- Off → On: ako ima tačno 2 On suseda
- On → Dying: uvek
- Dying → Off: uvek

**Iterativni proces:** Svaki korak generiše novo stanje cele mreže
