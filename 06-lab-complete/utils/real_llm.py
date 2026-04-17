from openai import OpenAI

_client = None

def get_client():
    global _client
    if _client is None:
        _client = OpenAI()  # đọc OPENAI_API_KEY từ env
    return _client

def ask(question: str, history: list = None) -> str:
    messages = []
    if history:
        for msg in history:
            if msg.startswith("User: "):
                messages.append({"role": "user", "content": msg[6:]})
            elif msg.startswith("Agent: "):
                messages.append({"role": "assistant", "content": msg[7:]})
    messages.append({"role": "user", "content": question})

    response = get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
    )
    return response.choices[0].message.content
