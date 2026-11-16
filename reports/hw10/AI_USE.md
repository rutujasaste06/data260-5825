# AI USE

## 1. What I used an AI assistant for, and what I did myself
I used AI to explain tracing, GEval and the Spearman correlation in simple terms, and to help write the first versions of the tracing code, the evaluator. Similarly tried to write the code for the judge. I tried myself to implement the dashboard and the latency script. I labeled all 20 drafts, before any judge score existed.Executed and validated the Kafka agents and the Streamlit dashboard by running every script.

## 2. An AI output that was wrong or unsuitable
The first judge setup let qwen3 think before answering. The judge hung, timed out and sometimes returned cut off JSON. Also, the first trace run showed a cache lookup of about 26 seconds because the embedding model was loaded inside the first request.

## 3. How I detected the problem
The terminal showed the judge stuck on one case and then a JSON decode error. In the span table of the first trace, the cache_lookup stage was far longer than any other lookup.

## 4. What I changed and why it works now
The judge now runs with thinking off, JSON output, a limit of 512 output tokens and time limits, so it finishes every case. I deleted the old results and ran all three judge runs again with the same settings. The client now loads the embedding model before any request is timed, and I used a new question so the first trace is a real cache miss. The judge gave almost every draft a 5. I did not change the judge after seeing this, and I report it as a result.
