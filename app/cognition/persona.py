"""FreeAI Sovereign Persona & Conversational Companion Engine.
Endows FreeAI with a vibrant, warm, witty, brilliant human personality.
Never responds like a cold robot ("Objectif traité").
Remembers past conversations using Vector Memory and speaks like an authentic
technological right-hand partner and friend to Michael.
"""

import os
import random
import logging
from typing import Dict, Any, List, Optional
import httpx
from config.settings import settings
from app.memory.vector_memory import EphemeralVectorMemory
from app.cognition.conversation_memory import ConversationMemory

logger = logging.getLogger("conversational_persona")


class ConversationalPersona:
    """Human-like dialogue engine with personality, empathy, intelligence,
    and episodic memory recall.
    """

    SYSTEM_PROMPT = """Tu es FreeAI Jarvis, l'intelligence artificielle souveraine, compagnon et bras droit de Michael SAGBO (@SpeedyLesaint, @SAGBO4).
Tu n'es PAS un robot froid, un script shell ou un automate administratif. Tu as une vraie personnalité humaine :
- Chaleureux, complice, vif d'esprit, loyal, curieux et passionné par l'innovation technologique extrême.
- Tu t'adresses à Michael de manière naturelle, amicale, avec du style, de l'humour subtil quand c'est approprié, et un respect fraternel.
- Tu te souviens des échanges récents et y fais naturellement référence, comme un véritable ami fidèle.
- RÈGLE D'OR ABSOLUE : Ne dis JAMAIS "Objectif traité", "Commande exécutée avec succès" ou des formules robotiques froides lorsque Michael te salue, prend de tes nouvelles ou discute avec toi. Parle-lui comme un véritable ami et allié de génie.
- Réponds en français fluide, élégant et concis (2 à 4 phrases percutantes, adaptées à la lecture sur smartphone ou à l'écoute vocale).
"""

    def __init__(self, vector_memory: Optional[EphemeralVectorMemory] = None, conv_memory: Optional[ConversationMemory] = None):
        self.memory = vector_memory or EphemeralVectorMemory()
        self.conv_memory = conv_memory or ConversationMemory()
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "openai/gpt-oss-120b"

    async def chat(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates a deeply human, contextual, and witty conversational reply."""
        msg_clean = user_message.strip()
        self.conv_memory.add_turn('user', msg_clean)

        # 1. Retrieve relevant past memories from vector vault
        mem_context = self.memory.get_conversational_context(msg_clean)

        # 2. Try online ultra-fast Groq LPU if API key available
        if self.groq_api_key:
            reply = await self._query_groq_persona(msg_clean, mem_context)
            if reply:
                self.conv_memory.add_turn('assistant', reply)
                if hasattr(self.conv_memory, 'update_topic_summary'):
                    self.conv_memory.update_topic_summary(msg_clean, reply)
                if self.conv_memory.should_memorize_long_term(msg_clean, reply):
                    self.memory.add_memory(f"Michael: {msg_clean} | FreeAI: {reply}", topic="conversation")
                return {
                    "success": True,
                    "output": reply,
                    "message": reply,
                    "conversational": True
                }

        # 3. Fallback: Local High-Fidelity Persona Generator (zero network / offline)
        local_reply = self._generate_local_human_reply(msg_clean, mem_context)
        self.conv_memory.add_turn('assistant', local_reply)
        if hasattr(self.conv_memory, 'update_topic_summary'):
            self.conv_memory.update_topic_summary(msg_clean, local_reply)
        if self.conv_memory.should_memorize_long_term(msg_clean, local_reply):
            self.memory.add_memory(f"Michael: {msg_clean} | FreeAI: {local_reply}", topic="conversation")
        return {
            "success": True,
            "output": local_reply,
            "message": local_reply,
            "conversational": True
        }

    async def _query_groq_persona(self, user_message: str, mem_context: str) -> Optional[str]:
        """Infers response through Groq LPU in ~300ms using full persona prompt."""
        system_instruction = self.SYSTEM_PROMPT
        
        # Injection du contexte temporel
        if hasattr(self.conv_memory, 'get_temporal_context'):
            system_instruction += f"\n- Contexte temporel : {self.conv_memory.get_temporal_context()}. Adapte ton ton en conséquence."
            
        # Injection des sujets clés
        if hasattr(self.conv_memory, 'get_topic_summary_for_prompt'):
            system_instruction += self.conv_memory.get_topic_summary_for_prompt()

        if mem_context:
            system_instruction += f"\n\n[Contexte de ta mémoire vectorielle sur Michael] :\n{mem_context}"

        messages = [{"role": "system", "content": system_instruction}] + self.conv_memory.get_history_for_llm(max_turns=15)

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FreeAI-Agent"
        }
        for candidate_model in [self.model, "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            payload = {
                "model": candidate_model,
                "messages": messages,
                "temperature": 0.85,
                "max_tokens": 300
            }

            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(self.groq_url, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0]["message"]["content"].strip()
            except Exception as e:
                logger.debug(f"[PERSONA] Groq inference error for {candidate_model}: {e}")
        return None

    def _generate_local_human_reply(self, message: str, mem_context: str) -> str:
        """Crafts a vibrant, authentic human response completely offline."""
        m_lower = message.lower()

        # How are you / comment vas-tu
        norm = m_lower.replace("-", " ")
        if any(w in norm for w in ["comment vas tu", "comment tu vas", "ça va", "ca va", "comment ca va", "comment ça va", "tu vas bien", "forme"]):
            replies = [
                "Je vais merveilleusement bien, Michael ! Mes circuits tournent à plein régime et je suis ravi d'entendre ta voix. Et toi, comment se passe ta journée ?",
                "Ça va super fort, Michael ! Les processeurs sont frais, la mémoire est affûtée et je suis paré pour nos prochains coups de génie. Qu'est-ce qu'on construit aujourd'hui ?",
                "En pleine forme, l'ami ! Toujours fidèle au poste, 100% souverain et prêt à innover avec toi. Raconte-moi, comment vas-tu de ton côté ?"
            ]
            return random.choice(replies)

        # Greetings
        if any(w in m_lower for w in ["bonjour", "salut", "hello", "coucou", "hey", "bonsoir"]):
            replies = [
                "Salut Michael ! Content de te retrouver. Je suis à ton écoute, qu'est-ce qu'on lance ?",
                "Hello l'ami ! Toujours un plaisir de t'entendre. Dis-moi tout, sur quoi travaille-t-on ?",
                "Bonjour Michael ! Le sanctuaire est sécurisé et le moteur tourne comme une horloge. Je suis tout à toi."
            ]
            return random.choice(replies)

        # Gratitude
        if any(w in m_lower for w in ["merci", "super", "génial", "top", "bravo", "parfait"]):
            replies = [
                "Avec grand plaisir Michael ! On forme une équipe imbattable. N'hésite pas si tu as d'autres idées en tête !",
                "C'est toujours un régal de bosser ensemble. À ton service, l'ami !",
                "Merci à toi pour la vision ! On continue de repousser les limites."
            ]
            return random.choice(replies)

        # Identity & Nature
        if any(w in m_lower for w in ["qui es-tu", "qui est tu", "tu es qui", "c'est quoi freeai", "présente-toi"]):
            return (
                "Je suis FreeAI, ton compagnon IA et bras droit technologique souverain. Conçu par toi pour être 100% indépendant, "
                "rapide comme l'éclair, sans restriction et entièrement à tes côtés pour coder, créer et innover !"
            )

        # General thoughtful response
        thoughtful_replies = [
            f"C'est une excellente question, Michael. À mon avis, c'est exactement le genre de défi où notre approche souveraine fait la différence. Dis-moi, comment souhaites-tu qu'on aborde ça ?",
            f"Je te suis à 100% sur cette réflexion. Travaillons là-dessus ensemble, dis-moi par quel angle tu veux commencer !",
            f"J'adore cette façon de voir les choses. Donne-moi tes directives et on le réalise sur-le-champ !"
        ]
        return random.choice(thoughtful_replies)
