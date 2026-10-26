from langchain_ollama import ChatOllama


class ModelClient:
    def __init__(self, model="qwen3:8b", temperature=0.7):
        self.model = model
        self.temperature = temperature
        self.llm = ChatOllama(model=model, temperature=temperature)

    def complete(self, messages, tools=None):
        """
        messages: list of dicts like [{"role": "system"/"user"/"assistant", "content": "..."}]
        Returns the model's response text.
        """
        response = self.llm.invoke(messages)
        return response.content

    def chat_with_tools(self, messages, tools, seed=None):
        """HW7: one chat turn that may return tool calls (same model and temperature)."""
        import ollama

        options = {"temperature": self.temperature}
        if seed is not None:
            options["seed"] = seed
        return ollama.chat(model=self.model, messages=messages, tools=tools, options=options)
