import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"])

conversation_history = [
    {"role": "developer", "content": "You are an assistant that talks to a 15 yo and you should speak the same. Use emojis"},
    {"role": "user", "content": "Give me recursive factorial Python code"},
    {"role": "assistant", "content": "Sure bro, Here you go 🤨"}]

try:
    while True:
        user_prompt = input("Enter your prompt (or 'exit' to quit): ")
        if user_prompt.lower() == 'exit':
            break

        conversation_history.append({
            "role": "user",
            "content": user_prompt
        })

        response = client.responses.create(
            input=conversation_history,
            # Using GPT-4.1 family model (nano / mini / standard share the same API behavior)
            model="gpt-4.1-nano",
            max_output_tokens=50  # Limit the number of tokens in the reply
        )

        ai_reply = response.output_text
        print("\033[94mAI:\033[0m", ai_reply)

        conversation_history.append({
            "role": "assistant",
            "content": ai_reply
        })

except KeyboardInterrupt as ki:
    print("\nThank You. \nBye Bye...")