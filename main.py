"""
Multimodal chatbot — CLI entry point (Gemini + Pollinations.ai edition).

Run with:  python main.py

Commands inside the chat:
    /remember <key> = <value>   store a long-term fact (e.g. /remember name = Harika)
    /forget <key>                remove a stored fact
    /memory                      show what's currently remembered
    /exit                        quit

Note: using /remember or /forget starts a fresh chat session internally
(so the updated facts take effect), which means Gemini's short-term
memory of the current conversation resets. Long-term facts are preserved
either way since those live in long_term_memory.json.
"""

from config import validate_config
from memory import LongTermMemory
from text_gen import create_chat, get_response


def build_system_prompt(long_term_memory: LongTermMemory) -> str:
    base = (
        "You are a helpful multimodal assistant. You can chat normally, and "
        "you can also generate images and videos when the user asks for them "
        "using the tools available to you."
    )
    memory_snippet = long_term_memory.as_system_prompt_snippet()
    if memory_snippet:
        return f"{base}\n\n{memory_snippet}"
    return base


def handle_command(command: str, long_term_memory: LongTermMemory) -> bool:
    """Returns True if the input was a command (and was handled)."""
    if command == "/exit":
        print("Goodbye!")
        raise SystemExit

    if command == "/memory":
        if long_term_memory.facts:
            print("Remembered facts:")
            for k, v in long_term_memory.facts.items():
                print(f"  - {k}: {v}")
        else:
            print("Nothing remembered yet.")
        return True

    if command.startswith("/remember "):
        body = command[len("/remember "):]
        if "=" not in body:
            print("Usage: /remember key = value")
            return True
        key, value = body.split("=", 1)
        long_term_memory.remember(key.strip(), value.strip())
        print(f"Remembered: {key.strip()} = {value.strip()}")
        return True

    if command.startswith("/forget "):
        key = command[len("/forget "):].strip()
        long_term_memory.forget(key)
        print(f"Forgot: {key}")
        return True

    return False


def main():
    validate_config()

    long_term = LongTermMemory()
    chat = create_chat(build_system_prompt(long_term))

    print("Multimodal Chatbot (Gemini + Pollinations.ai) — type /exit to quit, /memory to view stored facts.")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            handled = handle_command(user_input, long_term)
            if handled:
                # Facts may have changed — rebuild the chat session so the
                # system prompt reflects the latest long-term memory.
                if user_input.startswith(("/remember ", "/forget ")):
                    chat = create_chat(build_system_prompt(long_term))
                continue

        reply, files = get_response(chat, user_input)

        print(f"\nBot: {reply}")
        for f in files:
            print(f"  [generated file: {f}]")


if __name__ == "__main__":
    main()