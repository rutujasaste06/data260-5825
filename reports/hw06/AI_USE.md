# AI_USE - HW6 (Rutuja Saste, SID4 5825)

## 1. What I used AI for, and what I did myself
I used AI to explain each part of the homework in simple words and also used it for implementation of  the memory API, the Part 3 measurement script, and the file-memory chat program. I created the mongo db API by understanding previous assignment API implementations also took help of AI but tried at my level for better understanding, validated MongoDB, tested all commands. I also wrote the AGENT.md rules and chose the planted duplicates and contradictions in MEMORY.md.

## 2. One AI output that was wrong or unsuitable
The AI's first consolidation design asked qwen3:8b to rewrite the whole 55-line MEMORY.md. It only reached 52 lines, which fails the "under 40 lines" rule. A second design asked the model to group line numbers. It reached 29 lines, but it grouped unrelated lines so real facts were lost, and the contradictions were not resolved.

## 3. How I detected the problem
I counted lines with "wc -l" after each run and read the full MEMORY.md and dedupe_log.txt line by line. The 52-line result missed the line target. In the 29-line result I saw both Pfizer and Novartis still in the file and unrelated facts in the log. Later, "git diff" after "/compact" command showed that a second consolidation deleted "Resolved contradictions" lines.

## 4. What I changed and why it works now
I divided the task into smaller steps. First, the embedding model finds lines that may be similar. Then, the model checked each pair and labeled it as SAME, CONFLICT, or DIFFERENT. Python then kept the line with the newest date and saves all removed lines in a log. I also changed the consolidation code so it skips the “Resolved contradictions” section and adds new information to the log instead of replacing it. After these changes, MEMORY.md went from 55 lines to 35 lines. When I ran "/compact" again, "git diff" showed that only the timestamp had changed.
There are still some limitations. The port 8000 contradiction was resolved incorrectly because the newer line was not accurate, the correct API port is 8425. The system also did not detect the contradiction between using short bullets and long paragraphs.