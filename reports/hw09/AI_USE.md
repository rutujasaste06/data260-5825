# AI_USE.md - HW9

1. What I used an AI assistant for, and what I did myself
I used AI to explain Redis counters, vector search and cosine similarity in simple terms, to help write the first versions of the cache, threshold-sweep and two-agent code.. I tried to implement the agent self improving multi agent system by understanding the flow of how there is an improvement in agent learning process. Understood Docker and Redis command runs and accordingly ran every script on my machine
2. An AI output that was wrong or unsuitable
The first Part 4 revision prompt repeated my wrong earlier answer back to the model, and the model kept it, so the controlled revision test failed even with correct feedback. The evaluator also accepts any answer containing "not listed" as a correct refusal, which passed an invented estimate on test question te8.
3. How I detected the problem
The terminal output showed attempt 2 repeating "12 available slots" after the Evaluator had stated the correct value, and reading the final test answers one by one showed the invented estimate marked PASS.
4. What I changed and why it works now
The revision prompt now puts the Evaluator's correction in the system prompt as newer than the snapshot and no longer repeats the wrong answer, which made the controlled test pass. I added validation question va7 after the first validation pass kept an over-generalized lesson, and the gate then removed it. I did not change the evaluator after seeing the test results, I reported the te8 mis-scoring as a limitation instead.
