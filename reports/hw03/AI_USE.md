## 1. What did you use an AI assistant for, and what did you do yourself?

I used Claude to help me write the FastAPI auth code, the LlamaIndex chunking scripts for all three techniques.Made use of AI to understand concepts like sessions, cookies, embeddings, and cosine similarity in simple terms.

## 2. One AI-produced output that was wrong/unsuitable, or one thing you independently verified

While reviewing the retrieval results for Part 2, I noticed that the top Token Chunking result for  cinnamon-dose question appeared to be incorrect based on the shortened preview. To verify this, I ran a script to print the full chunk text and compared it directly with the original file. The complete chunk did contain the correct answer as “cinnamon at the dose of 1g daily” but this information appeared further down than what was shown in the preview. Therefore, the initial claim that the retrieval was incorrect was inaccurate.

## 3. How did you detect the problem or verify the result?

I detected the problem by printing the full chunk text instead of relying only on the shortened preview. When I reviewed the complete chunk, it clearly included the sentence “cinnamon at the dose of 1g daily,” further down in the same chunk. This confirmed that the top result did contain the correct answer and that the earlier claim that it was “confidently wrong” was inaccurate.

## 4. What did you change, and why does it work now?

I changed the example and used the full-text verification method before drawing a conclusion. Instead of relying on a shortened preview, I printed and reviewed the complete chunk. For the Semaglutide-versus-Ozempic question, I found that a highly similar chunk was actually about an unrelated trial involving Dapagliflozin and Forxiga. Since the full text confirmed that it did not address the question, this was a genuinely incorrect retrieval. This example is reliable because it was verified using the complete chunk content rather than a truncated preview.