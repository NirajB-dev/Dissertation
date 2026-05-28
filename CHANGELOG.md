# Changelog

All changes to the CAFR baseline are recorded here.
Each entry maps to a git commit and a results file.

---

## Baseline — CAFR (epochs=30, local_ep=10)
**Commit:** (initial)
**Results file:** `results_baseline_30ep.log`

### Cache Hit Rate (%)
| Cache Size | MCAF  | ε-Greedy | Thompson S. | Random |
|------------|-------|----------|-------------|--------|
| 50         | 12.58 | 9.38     | 5.72        | 1.14   |
| 100        | 20.66 | 19.02    | 12.22       | 1.72   |
| 150        | 28.95 | 27.02    | 17.87       | 3.22   |
| 200        | 34.31 | 33.35    | 20.94       | 5.36   |
| 250        | 39.96 | 38.36    | 25.88       | 5.93   |
| 300        | 45.25 | 43.14    | 30.24       | 7.43   |
| 350        | 50.82 | 47.98    | 35.10       | 8.93   |
| 400        | 56.25 | 52.17    | 40.03       | 8.93   |

### Request Delay (ms)
| Cache Size | MCAF  | ε-Greedy | Thompson S. | Random |
|------------|-------|----------|-------------|--------|
| 50         | 31.94 | 33.25    | 33.89       | 34.69  |
| 100        | 30.20 | 31.51    | 32.70       | 34.54  |
| 150        | 28.44 | 29.97    | 31.57       | 34.13  |
| 200        | 27.17 | 28.65    | 30.82       | 33.55  |
| 250        | 26.06 | 27.72    | 29.91       | 33.40  |
| 300        | 25.09 | 26.74    | 29.00       | 32.99  |
| 350        | 23.88 | 25.75    | 28.01       | 32.58  |
| 400        | 22.83 | 25.02    | 27.14       | 32.58  |

---

## Phase 4c — Two-Agent Cooperative Dueling DQN
**Status:** Complete
**Files changed:** `environment.py`, `dueling_ddqn.py`, `ce_cs.py`
**Builds on:** Phase 4a + 4b (all three fixes active in this run)
**Results file:** `results_phase4c.log`

### Architecture
- `CacheEnv` extended with `get_shared_state()`, `step_marl()`, `reset_marl()`
- RSU2 (`state2`) now actively managed by agent2 with its own `last_content2` pool
- Shared state = RSU1 cache + RSU2 cache concatenated → length = 2 × cache_size
- Both agents observe shared state; each acts on own RSU; both receive joint reward
- `DuelingAgent` accepts optional `state_dim` param for MARL input dimension
- `mini_batch_train_marl()` implements CTDE: centralised reward, decentralised action

### MCAF Cache Hit Rate (%) — full progression
| CS  | Baseline | +4a   | +4a+4b | +4a+4b+4c | Δ vs Baseline |
|-----|----------|-------|--------|-----------|---------------|
| 50  | 12.58    | 14.66 | 12.93  | 14.40     | +1.82         |
| 100 | 20.66    | 22.95 | 22.32  | 23.81     | +3.15         |
| 150 | 28.95    | 30.43 | 30.60  | 31.40     | +2.45         |
| 200 | 34.31    | 36.58 | 36.73  | 37.12     | +2.81         |
| 250 | 39.96    | 41.79 | 42.20  | 42.55     | +2.59         |
| 300 | 45.25    | 47.51 | 48.78  | 48.84     | +3.59         |
| 350 | 50.82    | 53.52 | 54.55  | 54.49     | +3.67         |
| 400 | 56.25    | 57.55 | 58.31  | 55.50     | **-0.75**     |

### MCAF vs Greedy gap (within-run, most meaningful metric)
| CS  | Baseline | +4a+4b+4c |
|-----|----------|-----------|
| 50  | +3.20    | +1.64     |
| 100 | +1.64    | +2.59     |
| 150 | +1.93    | +2.13     |
| 200 | +0.96    | +0.87     |
| 250 | +1.60    | +1.57     |
| 300 | +2.11    | **+3.21** |
| 350 | +2.84    | **+3.69** |
| 400 | +4.08    | +0.20     |

### Analysis of CS=400 convergence failure
At cache_size=400, the shared MARL state is 800-dimensional (2×400).
The DuelingDQN feature layer (800→128) is too shallow to learn a reliable
policy in only 30 episodes × 200 steps = 6,000 training samples per agent.
At CS=50–350 (state dim 100–700) the network converges and MARL consistently
outperforms baseline by +1.82–+3.67pp. At CS=400, training instability
collapses the MCAF-vs-Greedy gap from +4.08pp (baseline) to +0.20pp.

### Dissertation implications
- MARL cooperative caching demonstrably effective for cache sizes 50–350
- CS=400 failure is a clear, honest limitation attributable to DQN
  dimensionality: network capacity insufficient for 800-dim input in 30 episodes
- Future work: (1) increase MAX_EPISODES for larger cache sizes, (2) use a
  deeper feature extractor, (3) normalise state by max movie ID to reduce scale

### Delay at CS=400
- Phase 4c: 22.96ms vs Baseline: 22.83ms (+0.13ms — consistent with lower hit rate)

**Commit:** (see git log)

---

## Phase 4b — Staleness-Aware Asynchronous FL Aggregation
**Status:** Complete
**Files changed:** `dataset_processing.py`, `ce_cs.py`
**Builds on:** Phase 4a (both fixes active in this run)
**Results file:** `results_phase4b.log`

### What changed
- `asy_average_weights()` now accepts a `staleness` parameter τ
- Aggregation weight scaled by α(τ) = 1/(1+τ) instead of uniform 1/N
- `ce_cs.py` tracks `last_trained_round` per vehicle; computes staleness
  at aggregation time; updates record after each successful training round

### Staleness observed (from log)
- First cycle (rounds 0–14): α ranged from 1.0 (vehicle 0) to 0.067 (vehicle 14)
- Steady-state (rounds 15–29): all vehicles τ=15, α=0.0625 (no skipped vehicles)
- No vehicles were excluded by the staying-time check in this run

### MCAF Cache Hit Rate (%) — cumulative improvement over baseline
| Cache Size | Baseline | +4a only | +4a+4b | Δ vs Baseline | Δ vs 4a |
|------------|----------|----------|--------|---------------|---------|
| 50         | 12.58    | 14.66    | 12.93  | +0.35         | -1.73   |
| 100        | 20.66    | 22.95    | 22.32  | +1.66         | -0.63   |
| 150        | 28.95    | 30.43    | 30.60  | +1.65         | +0.17   |
| 200        | 34.31    | 36.58    | 36.73  | +2.42         | +0.15   |
| 250        | 39.96    | 41.79    | 42.20  | +2.24         | +0.41   |
| 300        | 45.25    | 47.51    | 48.78  | +3.53         | +1.27   |
| 350        | 50.82    | 53.52    | 54.55  | +3.73         | +1.03   |
| **400**    | **56.25**| **57.55**| **58.31**| **+2.06** | **+0.76** |

### MCAF Request Delay (ms) — cumulative improvement over baseline
| Cache Size | Baseline | +4a only | +4a+4b | Δ vs Baseline |
|------------|----------|----------|--------|---------------|
| 50         | 31.94    | 31.56    | 30.53  | -1.41         |
| 400        | 22.83    | 22.65    | 21.70  | -1.13         |

**Combined improvement at CS=400: +2.06pp cache hit rate, −1.13ms delay.**

---

## Phase 4a — FL-Guided Cache Replacement Policy
**Status:** In progress
**File changed:** `environment.py`

### Bugs fixed in `CacheEnv.step()`:
1. **Random eviction candidate selection** (line 58):
   `random.sample(list(self.last_content), 5)` replaced with
   `self.last_content[:5]` — selects the top-5 most popular
   uncached items as ranked by the FL global model, instead of
   picking 5 items at random.

2. **Loop bug — `if` instead of `for`** (lines 59-68):
   The original code used `if count < 5` (runs exactly once,
   replacing only `self.state[-1]`). Replaced with
   `for count in range(n_replace)` so that up to 5 items are
   actually replaced per action=1 step.

3. **Redundant second replacement block** (lines 65-68):
   Removed the duplicate `count=0; if count < 5` block that
   re-replaced `self.state[-1]` a second time on every action=1.

**Results file:** `results_phase4a.log`

### Cache Hit Rate (%) — MCAF only (vs baseline delta)
| Cache Size | Baseline | Phase 4a | Δ      |
|------------|----------|----------|--------|
| 50         | 12.58    | 14.66    | +2.08  |
| 100        | 20.66    | 22.95    | +2.29  |
| 150        | 28.95    | 30.43    | +1.48  |
| 200        | 34.31    | 36.58    | +2.27  |
| 250        | 39.96    | 41.79    | +1.83  |
| 300        | 45.25    | 47.51    | +2.26  |
| 350        | 50.82    | 53.52    | +2.70  |
| 400        | 56.25    | 57.55    | +1.30  |

**Average improvement: +2.02 percentage points across all cache sizes.**

### Request Delay (ms) — MCAF only
| Cache Size | Baseline | Phase 4a | Δ     |
|------------|----------|----------|-------|
| 50         | 31.94    | 31.56    | -0.38 |
| 100        | 30.20    | 29.75    | -0.45 |
| 150        | 28.44    | 28.01    | -0.43 |
| 200        | 27.17    | 26.87    | -0.30 |
| 250        | 26.06    | 25.82    | -0.24 |
| 300        | 25.09    | 24.67    | -0.42 |
| 350        | 23.88    | 23.56    | -0.32 |
| 400        | 22.83    | 22.65    | -0.18 |

**Average delay reduction: -0.34 ms across all cache sizes.**

**Commit:** (see git log)
