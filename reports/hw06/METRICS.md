# METRICS - HW6 Part 3

## Memory sweep and policy

| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |
|---|---|---|---|
| SHORT_TERM_N=4 | 243.4 | 4461.1 | 5.0 |
| SHORT_TERM_N=12 | 404.1 | 5104.8 | 4.4 |
| SHORT_TERM_N=30 | 687.5 | 5664.9 | 4.4 |
| Eviction/compression policy (N=12, older messages cut to 80 chars) | 365.0 | 4889.8 | 4.4 |

## Policy vs plain N=12

- Prompt-token savings: 9.7% (404.1 -> 365.0 per turn)
- Latency change: -215.0 ms
- Probe quality change: +0.00

## Cost estimate: 10,000 conversations x 30 turns ($1/M input, $5/M output)

| Setting | Mean prompt tokens/turn | Mean completion tokens/turn | Estimated cost |
|---|---|---|---|
| SHORT_TERM_N=4 | 243.4 | 23.9 | $108.89 |
| SHORT_TERM_N=12 | 404.1 | 25.9 | $160.09 |
| SHORT_TERM_N=30 | 687.5 | 27.1 | $246.87 |
| Eviction/compression policy (N=12, older messages cut to 80 chars) | 365.0 | 24.3 | $145.92 |

- Best setting: SHORT_TERM_N=4 (cheapest among settings within 0.5 quality points of the top score)
- Worst setting: SHORT_TERM_N=30 (highest estimated cost)
- Cost counts chat tokens only (not summary / fact-extraction calls).
