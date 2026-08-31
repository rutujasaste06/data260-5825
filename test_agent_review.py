import sys
sys.path.append("src")
from model_client import ModelClient

with open("AGENT.md", "r") as f:
    agent_instructions = f.read()

client = ModelClient()

messages = [
    {"role": "system", "content": agent_instructions},
    {"role": "user", "content": """Please review this code:

def add(a, b):
    result = a+b
    return(result)
"""}
]

response = client.complete(messages)
print("=== Model Response ===")
print(response)