
## Part 3: fault injection (VERIFY_SEED = 265825, 50 calls per rate)
| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |
|---|---|---|---|
| 0% | 100.0% | 0.99 | 3.10 |
| 20% | 100.0% | 35.40 | 355.13 |
| 50% | 94.0% | 103.93 | 355.86 |

## Part 3: retry demos
| Demo | Attempts used | Latency (ms) | Result |
|---|---|---|---|
| Success on the first attempt | 1 | 37.5 | ok: True |
| Failure first, then success after a retry | 2 | 54.5 | ok: True |
| Failure after all retries | 4 | 352.8 | ok: False, clean error, no crash |

## Part 4: offline tests
11/11 passed (9 Part 4 tests + safety block + agent max_steps with MockModel).

## Part 5: safety rule
| Call | Result |
|---|---|
| search_trials, limit 5 | allowed, ok: true |
| search_trials, limit 100 | blocked, ok: false, "safety rule: ..." |

## Part 5: agent scenarios (local model qwen3:8b via Ollama, max_steps = 5)
| Scenario | Steps | Stop reason | Tool calls |
|---|---|---|---|
| How many trials does sponsor 1 have, and how many slots in total? | 2 | completed | 1 |
| Find trials about Diabetes and tell me the first one's NCT number. | 2 | completed | 1 |
| Look up trial 5001 and name its sponsor. | 2 | completed | 1 |
| Give me 100 trials about Metformin. | 4 | completed | 3 (1 blocked by safety rule) |
'@ | Set-Content reports\hw05\METRICS.md