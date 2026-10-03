from datetime import datetime
import json
import gzip
import re
from typing import List, Dict, Any, Optional

class ConversationMemory:
    def __init__(self):
        self.turns: List[Dict[str, Any]] = []
        self.topic_summary: List[str] = []

    def add_turn(self, role: str, content: str, message_id: Optional[int] = None) -> None:
        self.turns.append({
            "role": role,
            "content": content,
            "message_id": message_id
        })

    def get_history_for_llm(self, max_turns: int = 15) -> List[Dict[str, str]]:
        history = self.turns[-max_turns:] if max_turns > 0 else self.turns
        return [{"role": turn["role"], "content": turn["content"]} for turn in history]

    def get_summary(self) -> str:
        if not self.turns:
            return "Aucun sujet en cours."
        last_user = next((t["content"] for t in reversed(self.turns) if t["role"] == "user"), None)
        if last_user:
            return f"Sujet récent: {last_user[:50]}..."
        return "Sujet en cours..."

    def is_tagged_mention(self, text: str, bot_username: str = 'LesaintAi_bot') -> bool:
        if not text:
            return False
        return f"@{bot_username.lower()}" in text.lower()

    def should_memorize_long_term(self, text: str, response: str) -> bool:
        combined = f"{text} {response}".lower()
        heuristics = [
            re.search(r'\b(préfère|aime|déteste|veux)\b', combined),
            re.search(r'\b(projet|décision|techno|architecture)\b', combined),
            re.search(r'\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|demain|hier|\d{1,2}/\d{1,2})\b', combined)
        ]
        
        # Check for proper nouns like names (heuristic: capitalized words not at start, though in lowercase we can't easily, let's just use some keywords)
        # We can look at the original text for capitalized words inside the sentence
        proper_noun_pattern = re.compile(r'(?<!^)\b[A-Z][a-z]+\b')
        has_proper_noun = bool(proper_noun_pattern.search(text)) or bool(proper_noun_pattern.search(response))

        return any(heuristics) or has_proper_noun

    def serialize_to_gzip(self) -> bytes:
        json_str = json.dumps(self.turns, ensure_ascii=False)
        return gzip.compress(json_str.encode('utf-8'))

    @classmethod
    def restore_from_gzip(cls, data: bytes) -> 'ConversationMemory':
        instance = cls()
        if not data:
            return instance
        try:
            json_str = gzip.decompress(data).decode('utf-8')
            instance.turns = json.loads(json_str)
        except Exception:
            pass
        return instance

    def clear(self) -> None:
        self.turns = []

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def get_temporal_context(self) -> str:
        hour = datetime.now().hour
        if 22 <= hour or hour < 6:
            return "22h00-06h00 (Nuit) : Ton complice et détendu ('Encore debout Maître ? 🌙 ...')"
        elif 6 <= hour < 9:
            return "06h00-09h00 (Matin) : Ton énergisant matinal"
        elif 9 <= hour < 18:
            return "09h00-18h00 (Journée) : Ton efficace et focus"
        else:
            return "18h00-22h00 (Soirée) : Ton chaleureux et soirée"

    def update_topic_summary(self, user_msg: str, assistant_msg: str) -> None:
        # Simple extraction of keywords for semantic summary
        combined = f"{user_msg} {assistant_msg}"
        # A simple mock logic to extract some topics
        words = [w for w in combined.split() if len(w) > 5 and w.istitle()]
        if not words:
            words = [w for w in user_msg.split() if len(w) > 4][:2]
        
        topic = " ".join(words[:2]) if words else "Discussion générale"
        if len(topic) > 30:
            topic = topic[:27] + "..."
            
        self.topic_summary.append(topic)
        if len(self.topic_summary) > 5:
            self.topic_summary.pop(0)

    def get_topic_summary_for_prompt(self) -> str:
        if not self.topic_summary:
            return ""
        return "\n[Sujets clés de la session : " + ", ".join(self.topic_summary) + "]"
