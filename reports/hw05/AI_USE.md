# AI_USE.md

## 1. What I used an AI assistant for, and what I did myself
I used AI to explain the assignment,understand and write the code for Redux slice, MCP servers, retry logic and fix errors. I did all the validations against MCP server. Updated the SQL tables by including the sponsor table and linking it with the trials table. DId overall changes for thw flow and also ran the verification tests. 

## 2. One AI-produced output that was wrong or unsuitable
The AI gave me MCP server code using `FastMCP`, but `pip install "mcp[cli]"` installed MCP 2.x, where that class was renamed, so `mcp dev` failed with `No module named 'mcp.server.fastmcp'`. Other AI problems I hit: a stray period in AI-written comments in seed_hw4.py caused a SyntaxError on my second laptop; `jinja2` was missing from the AI's install list; and in scenario 4 the agent said "24 trials" while the tool result had 25 rows.

## 3. How I detected the problem
The MCP error message named the rename directly, and I confirmed the installed version with `pip show mcp` (2.3.0). The other issues showed up as errors when I ran the code on a clean machine, and I counted the rows in agent_runs.jsonl to catch the "24 vs 25" mistake.

## 4. What I changed and why it works now
I pinned `mcp<2` (1.30.0), which has `FastMCP`, and launched the Inspector with my venv Python instead of `uv`; both servers now connect. I removed the stray periods, installed `jinja2`, and set `DATABASE_URL`, so the backend and seed run on both laptops. For the agent, I documented that a model's summary must be checked against the tool result.