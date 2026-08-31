# data260-5825

DATA-260 Homework 1 — Rutuja Saste (SID4: 5825)
Domain: Clinical Trial Listings (DOMAIN_ID 1)

## Configuration
- PORT_BASE: 8425
- PREFIX: s5825
- SEED: 5825
- VERIFY_SEED: 265825

## Repository Structure

```
data260-5825/
├── code/
│   ├── web_application/
│   │   ├── index.html
│   │   ├── script.js
│   │   └── Dockerfile
│   ├── agents_demo.py
│   ├── hw1_client.py
│   ├── run_experiments.py
│   ├── analyze_results.py
│   ├── test_agent_review.py
│   └── verify.py
├── src/
│   └── model_client.py
├── reports/
│   └── hw01/
├── AGENT.md
├── DOMAIN_SCHEMA.md
└── README.md
```

## Prerequisites
- Python 3.11 or 3.12
- Docker Desktop
- Ollama (with `qwen3:8b` pulled: `ollama pull qwen3:8b`)
- AWS CLI (configured with `aws configure`)

## Part I & II — HTML/JS Form

Open `code/web_application/index.html` directly in a browser, or serve via Docker (see below).

## Docker (Local Deployment)

```
cd code/web_application
docker build -t clinical-trial-app .
docker run -d -p 8080:80 --name clinical-trial-container clinical-trial-app
```

Visit: http://localhost:8080

## AWS ECS Deployment

```
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 093468662825.dkr.ecr.us-east-2.amazonaws.com
docker tag clinical-trial-app:latest 093468662825.dkr.ecr.us-east-2.amazonaws.com/clinical-trial-app:latest
docker push 093468662825.dkr.ecr.us-east-2.amazonaws.com/clinical-trial-app:latest
```

Then deploy via AWS Console: ECS Cluster (Fargate) → Task Definition → Service (with public IP enabled).

## Part 2 — Agentic AI

```
python -m venv venv
venv\Scripts\activate
pip install langchain langchain-ollama
cd code
python agents_demo.py --temp 0.7
```

## Part 3 — Non-Determinism Experiment

```
cd code
python run_experiments.py
python analyze_results.py
```

Results saved to `reports/hw01/raw/` and `reports/hw01/METRICS.md`.

## Part 4 — Model Client

```
cd code
python hw1_client.py
```

Type messages, use `/stats` for stats, `exit` to quit.

Test AGENT.md instruction-following:

```
cd code
python test_agent_review.py
```

## Verification

```
cd code
python verify.py
```

Outputs `reports/hw01/verification.json`.

## Part 4 — Written Answers

Questions:
1.	why is prior conversation context resent with every turn?
The AI has no memory. Everytime a message is sent the AI forgets everything the second the conversation ends. Hence to remember the conversation, the app must resend the full conversation every time just to remind it what’s already been said. 
2.	How is a system prompt different from a user message? 
The system prompt is the fixed rule that is set at once for how the AI should behave whereas the user message is the actual question or task you ask it to do and it will change every time.
3.	Why do input tokens grow over a conversation? 
To remind AI the full conversation we have to resend it every time and hence it keeps getting bigger and bigger the more we talk. This is what my numbers showed, going from 13 tokens  on turn 1  to over 1700  by turn 5.
4.	What eventually limits that growth?
Every AI model has a maximum size limit for how much text it can read at once, so eventually a long conversation would hit that limit and either break or need older messages trimmed out.

## GitHub Repository

https://github.com/rutujasaste06/data260-5825


