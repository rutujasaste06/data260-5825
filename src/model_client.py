from langchain_ollama import ChatOllama

class ModelClient:
    def __init__(self, model="qwen3:8b", temperature=0.7):
        self.llm = ChatOllama(model=model, temperature=temperature)

    def complete(self, messages, tools=None):
        """
        messages: list of dicts like [{"role": "system"/"user"/"assistant", "content": "..."}]
        Returns the model's response text.
        """
        response = self.llm.invoke(messages)
        return response.content