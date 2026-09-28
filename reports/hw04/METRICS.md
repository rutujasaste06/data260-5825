| Page size | Version | SQL stmts/req | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|
| 10 | naive | 11 | 3.78 | 4.08 | 4.15 |
| 10 | fixed | 1 | 1.67 | 1.77 | 1.79 |
| 50 | naive | 51 | 7.38 | 9.59 | 10.47 |
| 50 | fixed | 1 | 1.56 | 1.66 | 1.68 |
| 200 | naive | 201 | 25.13 | 28.3 | 33.4 |
| 200 | fixed | 1 | 2.43 | 2.65 | 8.66 |

Speed-up (naive p50 / fixed p50):
- size 10: 2.3x
- size 50: 4.7x
- size 200: 10.3x
