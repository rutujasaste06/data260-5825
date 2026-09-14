## 1. What did you use an AI assistant for, and what did you do yourself?

I used Claude for: explaining LangGraph concepts (AgentState, nodes, the Supervisor pattern, conditional routing) in plain language before implementing them, generating initial code for the FastAPI backend (CRUD endpoints), helping debug errors I encountered while running the code. Also used W3schools for python and javascript coding understanding
I did the actual implementation for CSS and js script changes to develop the interactive webpage. Analysed and connected the frontend and backend by doing necessary code changes in main.py file and script.js file. Did code changes in the experiments file to perform 30 runs. Validated the outputs, generated the report.

## 2. One AI-produced output that was wrong/unsuitable, or one thing you independently verified

During the LangGraph refactor (Part 3), the code part for extracting the final output after the graph finished running had a bug: it only read the state from the very last node that executed (the Supervisor), which does not carry the Planner's actual tags and summary. As a result, running the script printed "tags": null, "summary": null in the Finalized Publish Output, even though the Planner and Reviewer had both completed successfully earlier in the run. Made the changes in the code after verifying the misleading output.

## 3. How did you detect the problem or verify the result?

I detected this by actually running the script myself and reading the real terminal output line by line, rather than assuming the code was correct. The Planner and Reviewer sections clearly showed valid tags and a summary being produced, but the final "Finalized Publish Output" section printed null values a clear mismatch between what the graph had actually produced and what the final print statement displayed.

## 4. What did you change, and why does it work now?

I changed the code so it collects the output from every step of the graph, not just the last one. Before, it only looked at whatever the Supervisor did last, which never included the tags or summary. Now it keeps adding each node's result to the state as the graph runs, so the final output correctly shows the Planner's tags and summary no matter which node ran last. I confirmed the fix by executing the script again and checking that the final output matched what the Planner and Reviewer had actually produced earlier in the same run.