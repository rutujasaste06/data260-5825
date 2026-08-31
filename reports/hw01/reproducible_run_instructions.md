# Reproducible Run Instructions — HW1

See full details in the root `README.md`. Summary below:

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install langchain langchain-ollama
ollama pull qwen3:8b
```

## Part I & II — HTML/JS Form

Open `code/web_application/index.html` in a browser, or run via Docker:

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

Then deploy via AWS Console: ECS Cluster (Fargate) → Task Definition → Service (public IP enabled).

## Part 2 — Agentic AI

```
cd code
python agents_demo.py --temp 0.7
```

## Part 3 — Non-Determinism Experiment

```
cd code
python run_experiments.py
python analyze_results.py
```

## Part 4 — Model Client

```
cd code
python hw1_client.py
python test_agent_review.py
```

## Verification

```
cd code
python verify.py
```

## GitHub Repository

https://github.com/rutujasaste06/data260-5825