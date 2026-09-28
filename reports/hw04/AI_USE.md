# AI_USE.md

## 1. What I used an AI assistant for, and what I did myself

I used Claude code to understand RAG and also write the RAG scripts for Part 4. Also for understanding the React coding I used W3 schools and chatgpt to get easier explanation of how it works and for the scripts to understand. For frontend took help of AI to correct the scripts if wrong. Also to understand the commands and execute them for RAG took help of AI.

I did the following myself: installed and configured MySQL, wrote the scripts for frontend by understanding using different websites and AI as well, created the database and ran the seed script, ran every Postman request, read every generated answer in configs A/B/C to check it against the source documents, and wrote the final analysis text based on my own reading of the results.

## 2. One AI-produced output that was wrong or unsuitable

In Part 4, my first version of the context-engineered RAG prompt (grounding rules v1) answered Q5 ("What was the p99 latency of the fixed endpoint at page size 200 in the second measurement run?") with "2.43 ms". This was wrong: the documents only state a median latency of 2.43ms
at page size 200, and never state a p99 value or mention a "second run". The model treated a related number as if it answered the question.

## 3. How I detected the problem

I compared the generated answer against the actual source document (04_n_plus_one.txt) and confirmed it does not contain the word "p99" anywhere near the 2.43 ms figure, and never mentions a second measurement run at all. The assignment requires Q5 to be refused, so I knew
this was a failure even before checking the wording closely.

## 4. What I changed and why it works now

I first tried making the grounding instructions stricter in two versions, v1 and v2. I also tested an LLM-based verification step in v3, where the model reviewed its own context before answering. However, none of these methods prevented the hallucination. The small local model continued to treat the related median value as close enough to the requested answer, even though the question specifically asked for p99.
The solution was to add a simple Python check before sending the question to the LLM. This check looks for the exact metric mentioned in the question, such as p99, p95, p50, median, mean, or the word “second.” It then searches the retrieved text to see whether that exact term is present.
If the requested term is missing from the retrieved chunks, the system refuses to answer instead of guessing. This approach is deterministic because it is handled by code rather than depending on the model to judge whether the evidence is sufficient.
After adding this check, the system correctly refused Q5 because the retrieved documents did not contain a p99 value. The other questions, Q1–Q4 and Q6, were not affected. This shows that the code-level validation successfully addressed the hallucination while allowing questions with adequate supporting evidence to continue normally.