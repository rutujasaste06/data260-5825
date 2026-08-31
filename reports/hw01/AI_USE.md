(1) what you used an AI assistant for and what you did yourself?
I used claude as a guide throughout this assignment for explaining few concepts such as Docker, Langchain, HTML/JS features, helping troubleshoot errors (AWS free-tier signup issues, WSL/Docker setup, CloudWatch permissions, subprocess/venv Python path issues). ALso took help from claude and copilot to understand the code structures for agents_demo.py, model_client.py and hw1_client.py. I typed all commands myself, made all configuration decisions (domain schema fields, security group settings, resource naming), ran every test personally, and reviewed/verified all outputs before accepting them into the final submission.

(2) one AI-produced output that was wrong/unsuitable, or one thing you independently verified; 
the initial version of run_experiments.py used subprocess.run(["python", "agents_demo.py"]) to call the agent script repeatedly. This failed the tests of all 40 runs silently and returned empty tags with fast latencies (30-50ms instead of the expected 30+ seconds).

(3) how you detected the problem or verified the result; 
I detected the problem by noticing that normally the AI takes 30+ seconds to think and respond, but our failed runs were finishing in less than a second, hence I added explicit error printing (stderr output) to the script, which revealed a ModuleNotFoundError: No module named 'langchain_ollama' and this way understood where the issue is.

(4) what you changed and why it works now.
My script accidentally used the wrong version of Python that didn't have the needed packages installed, causing every run to fail instantly. I fixed it by telling the script to always use the exact same Python it was already running with. After fixing it, I tested with just 1 quick run first to make sure it worked, and once that succeeded, I ran the full batch of 40 tests, which completed successfully this time.