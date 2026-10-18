# Agent Instructions

## Code review responses
- When asked to review code, you MUST respond using ONLY bullet points.
- Do not include any introductory sentences, paragraphs, explanations outside of bullets, or concluding remarks. Every piece of feedback must be a single bullet point starting with "- ".
- Do not use headings, code blocks, or numbered lists in review responses. Bullet points only.

## Project description
- This project is a Clinical Trial Listings system: FastAPI + MongoDB APIs and a chat assistant with memory.
- The student is Rutuja Saste (SID4 5825). Explain things in simple words.

## Technology stack
- Use Python 3.11, FastAPI, PyMongo and Pydantic.
- The local model is qwen3:8b through Ollama. Do not call paid hosted models.

## Coding conventions
- Every function must have type hints and a one-line docstring.
- Use snake_case names and keep each function under 20 lines.
- Application functions must not use print(). Use logging. Only the chat CLI may print.

## Testing approach
- Every new function needs at least one pytest test in a tests/ folder.

## Prohibited actions
- Never hard-code passwords, API keys or database credentials.
- Do not edit code/doc_api or code/memory_api unless asked.