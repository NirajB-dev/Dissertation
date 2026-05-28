# Cooperative Caching in VEC via Asynchronous FL and DRL

> **Trinity College Dublin — MSc Dissertation (2025–26)**  
> Extended implementation of the CAFR framework with three research improvements.

---

## Overview

This codebase implements **CAFR** — a cooperative content caching framework for Vehicular Edge Computing (VEC) that combines:

- **Asynchronous Federated Learning (AFL)** to predict content popularity across vehicles
- **Deep Reinforcement Learning (DRL)** — Dueling Double DQN — to make cache replacement decisions at RSUs

The dissertation extends the baseline with three research phases:

| Phase | Contribution | Avg Hit Rate Δ |
|-------|-------------|----------------|
| 4a | FL-guided cache replacement (fixes random eviction bug) | +2.03 pp |
| 4b | Staleness-aware async FL aggregation (α = 1/(1+τ)) | +0.18 pp marginal |
| 4c | Two-agent cooperative MARL (CTDE, shared reward) | +0.31 pp marginal |
| **Full** | All three combined | **+2.52 pp, −2.47 ms** |

---

## Repository Structure

```
.
├── ce_cs.py                  # Main entry point — run this
├── environment.py            # CacheEnv: RL environment + MARL extensions
├── dueling_ddqn.py           # DuelingAgent + training loops (single & MARL)
├── dataset_processing.py     # FL data sampling + staleness-aware aggregation
│
├── model.py                  # AutoEncoder (FL) + DuelingDQN (RL) models
├── local_update.py           # Local FL training, cache hit ratio helpers
├── cv2x.py                   # C-V2X channel simulation (V2I, MBS)
├── select_vehicle.py         # Vehicle mobility & position selection
├── user_cluster_recommend.py # FL-based recommendation engine
├── Thompson_Sampling.py      # Thompson Sampling baseline
├── data_set.py               # MovieLens data conversion utilities
├── user_info.py              # User info helpers
├── options.py                # CLI argument parser (--epochs, --local_ep, etc.)
├── replay_buffers.py         # Experience replay buffer for DQN
├── utils.py                  # Misc utilities (ModelManager, count_top_items)
│
├── results/                  # Experiment logs
│   ├── results_baseline_30ep.log
│   ├── results_phase4a.log
│   ├── results_phase4b.log
│   ├── results_phase4c_v2.log   # Phase 4c with convergence fixes
│   └── results_phase4d_ablation.log
│
├── legacy/                   # Original scripts from base paper (not modified)
│   ├── ce_dl.py              # Alternate entry: delay-based training
│   ├── ce_round.py           # Alternate entry: round-based training
│   ├── ce_rp_cs.py           # Alternate entry: replacement + cache size sweep
│   ├── main_avg.py           # Synchronous FL (FedAvg) baseline
│   └── plot.py               # Plotting utilities for paper figures
│
├── data/                     # Processed MovieLens-1M data
│   └── ml-1m/
├── CHANGELOG.md              # Phase-by-phase results and analysis
└── README.md
```

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch numpy scipy tqdm matplotlib pandas
```

---

## Running

```bash
# Standard run (epochs=30, local_ep=10) — ~2–3 hours
python ce_cs.py --epochs 30 --local_ep 10

# Keep running when laptop lid is closed (macOS)
caffeinate -i python ce_cs.py --epochs 30 --local_ep 10 | tee results/my_run.log
```

### Key arguments (`options.py`)

| Flag | Default | Description |
|------|---------|-------------|
| `--epochs` | 10 | FL global rounds (30 = paper quality) |
| `--local_ep` | 10 | Local epochs per vehicle per round |
| `--clients_num` | 15 | Number of vehicles |
| `--lr` | 0.01 | Base learning rate |
| `--gpu` | None | GPU device index |

---

## System Architecture

```
Vehicles (15)
    │  V2I channel (async, one per FL round)
    ▼
RSU 1 ──── Agent 1 (DuelingDQN)
RSU 2 ──── Agent 2 (DuelingDQN)   ← Phase 4c: cooperative MARL
    │  Both observe shared state = RSU1 cache ∥ RSU2 cache
    │  Both receive joint delay-minimisation reward
    ▼
MBS (fallback, highest latency)
```

**FL loop (async):** One vehicle trains per global round (round-robin). Aggregation uses staleness weight α(τ) = 1/(1+τ) where τ = rounds since last training (Phase 4b).

**RL loop (end of training):** For each cache size ∈ {50,100,…,400}, run `MAX_EPISODES = max(30, int(30·√(c_s/50)))` episodes of 200 steps each. Cache replacement policy: replace 5 least-popular cached items with 5 most-popular uncached items (FL-ranked).

---

## Results Summary

See `CHANGELOG.md` for full per-phase results.  
See `results/results_phase4d_ablation.log` for the complete ablation study.

### Cache Hit Rate (%) — MCAF vs baselines (Phase 4c v2)

| Cache Size | **MCAF** | ε-Greedy | Thompson S. | Random |
|------------|----------|----------|-------------|--------|
| 50         | **13.49** | 10.44 | 6.18 | 0.68 |
| 100        | **22.76** | 21.07 | 15.15 | 3.17 |
| 200        | **36.93** | 36.39 | 29.01 | 5.12 |
| 400        | **59.23** | 56.06 | 55.09 | 10.55 |

MCAF outperforms ε-Greedy at every cache size.

---

## Dataset

**MovieLens-1M** — used as a proxy for vehicular content requests.
- 1,000,209 ratings | 3,883 movies | 6,040 users
- Mapped to 15 vehicles via user clustering

---

## Citation

Base paper:
> *Cooperative Caching in Vehicular Edge Computing via Asynchronous Federated Learning and Deep Reinforcement Learning* — IEEE (2023)
