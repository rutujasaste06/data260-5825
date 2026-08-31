import sys
sys.path.append("src")
from model_client import ModelClient

def count_tokens(text):
    # Simple approximation: ~4 characters per token (common rule of thumb)
    return max(1, len(text) // 4)

def main():
    client = ModelClient()
    conversation_history = []
    system_prompt = {"role": "system", "content": "You are a helpful assistant."}
    conversation_history.append(system_prompt)

    cumulative_input_tokens = 0
    cumulative_output_tokens = 0
    turn_count = 0

    print("HW1 Model Client — type your message, or '/stats' for stats, or 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.strip().lower() == "exit":
            break

        if user_input.strip().lower() == "/stats":
            history_length = sum(len(m["content"]) for m in conversation_history)
            print(f"\n--- STATS ---")
            print(f"Turn count: {turn_count}")
            print(f"Cumulative input tokens: {cumulative_input_tokens}")
            print(f"Cumulative output tokens: {cumulative_output_tokens}")
            print(f"Cumulative total tokens: {cumulative_input_tokens + cumulative_output_tokens}")
            print(f"Serialized conversation history length: {history_length} characters")
            print(f"-------------\n")
            continue

        conversation_history.append({"role": "user", "content": user_input})

        input_text_this_turn = " ".join(m["content"] for m in conversation_history)
        input_tokens = count_tokens(input_text_this_turn)

        response_text = client.complete(conversation_history)

        output_tokens = count_tokens(response_text)

        conversation_history.append({"role": "assistant", "content": response_text})

        turn_count += 1
        cumulative_input_tokens += input_tokens
        cumulative_output_tokens += output_tokens

        print(f"\nAssistant: {response_text}")
        print(f"[Turn {turn_count} — Input tokens: {input_tokens}, Output tokens: {output_tokens}, Total: {input_tokens + output_tokens}]\n")

    print(f"\n=== Session ended ===")
    print(f"Total turns: {turn_count}")
    print(f"Cumulative input tokens: {cumulative_input_tokens}")
    print(f"Cumulative output tokens: {cumulative_output_tokens}")
    print(f"Cumulative total tokens: {cumulative_input_tokens + cumulative_output_tokens}")

if __name__ == "__main__":
    main()