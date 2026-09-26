"""LLM backends: local Ollama, or Hugging Face's hosted Inference API.
Both are thin wrappers over their official client packages - select one
via the LLM_BACKEND env var (ollama|hf). No other backends are supported.
"""
import os


def _messages(system: str, history: list, user_message: str) -> list:
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def ollama_reply(system: str, history: list, user_message: str) -> str:
    import ollama

    client = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    response = client.chat(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        messages=_messages(system, history, user_message),
    )
    return response["message"]["content"].strip()


def hf_reply(system: str, history: list, user_message: str) -> str:
    from huggingface_hub import InferenceClient

    client = InferenceClient(token=os.environ["HF_API_TOKEN"])
    response = client.chat_completion(
        messages=_messages(system, history, user_message),
        model=os.environ.get("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def get_reply(system: str, history: list, user_message: str) -> str:
    backend = os.environ.get("LLM_BACKEND", "ollama").lower()
    if backend == "hf":
        return hf_reply(system, history, user_message)
    return ollama_reply(system, history, user_message)
