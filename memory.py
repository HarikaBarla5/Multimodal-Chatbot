"""
Long-term memory, persisted to a JSON file on disk. Stores facts the bot
should remember across sessions (e.g. "user's name is Harika", "user
prefers concise answers"). This is loaded into the system prompt at
startup so Gemini "remembers" the user between runs.

Note: short-term (within-session) conversation history is now handled
automatically by Gemini's chat session object (see text_gen.create_chat),
so there's no separate ShortTermMemory class needed here anymore.
"""

import json
import os
from config import LONG_TERM_MEMORY_FILE


class LongTermMemory:
    def __init__(self, filepath=LONG_TERM_MEMORY_FILE):
        self.filepath = filepath
        self.facts = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2)

    def remember(self, key, value):
        """Store a fact, e.g. remember('name', 'Harika')"""
        self.facts[key] = value
        self._save()

    def forget(self, key):
        if key in self.facts:
            del self.facts[key]
            self._save()

    def as_system_prompt_snippet(self):
        """Turn stored facts into text that gets injected into Gemini's system prompt."""
        if not self.facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in self.facts.items()]
        return "Known facts about the user from past sessions:\n" + "\n".join(lines)