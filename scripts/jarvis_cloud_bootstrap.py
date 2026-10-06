import os
import sys
import time
import json
import asyncio
import httpx
import argparse
import random
from pathlib import Path

MODEL_CASCADES = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    },
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat"]
    },
    "openrouter_free": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["meta-llama/llama-3-8b-instruct:free"]
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "models": ["gemini-1.5-flash"]
    }
}

class SovereignSwarmClient:
    def __init__(self):
        self.keys = {
            "groq": os.environ.get("GROQ_API_KEY", ""),
            "deepseek": os.environ.get("DEEPSEEK_API_KEY", ""),
            "openrouter_free": os.environ.get("OPENROUTER_API_KEY", ""),
            "gemini": os.environ.get("GEMINI_API_KEY", "")
        }
        self.provider_status = {
            p: "READY" if k else "NO_KEY" for p, k in self.keys.items()
        }

    async def query_provider_cascade(self, client: httpx.AsyncClient, provider_id: str, prompt: str):
        if self.provider_status[provider_id] != "READY":
            return None, None
            
        key = self.keys.get(provider_id)
        if not key:
            return None, None
            
        cascade = MODEL_CASCADES.get(provider_id)
        if not cascade:
            return None, None
        
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        for model in cascade["models"]:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500
            }
            try:
                res = await client.post(cascade["url"], headers=headers, json=payload, timeout=20.0)
                if res.status_code == 402:
                    self.provider_status[provider_id] = "PAYMENT_REQUIRED_402"
                    return None, None
                if res.status_code == 400:
                    continue
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"].strip()
                return model, content
            except Exception as e:
                continue
                
        return None, None

async def send_telegram_message(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram non configuré.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=10.0)
            res.raise_for_status()
            return True
    except Exception as e:
        print(f"Erreur Telegram: {e}")
        return False

async def run_swarm_bootstrap(num_topics: int, notify_telegram: bool):
    swarm = SovereignSwarmClient()
    
    topics = [
        "Astuce avancée en Python pour l'optimisation mémoire",
        "Principe de sécurité zero-trust",
        "Concept d'innovation IA décentralisée",
        "Astuce noyau Linux méconnue",
        "Philosophie tech souveraine",
        "L'avenir des interfaces neurales",
        "Optimisation extrême des appels base de données",
        "Bypass de limites de tokens LLM avec l'agentic workflow",
        "Docker multi-stage secret"
    ]
    
    selected_topics = [random.choice(topics) for _ in range(num_topics)]
    results = []
    
    async with httpx.AsyncClient() as client:
        for i, topic in enumerate(selected_topics):
            print(f"[{i+1}/{num_topics}] Sujet: {topic}")
            prompt = f"Génère une brève explication (3 phrases) très pointue sur le sujet suivant: {topic}. Ne mets pas de blabla introductif."
            
            tasks = [
                swarm.query_provider_cascade(client, "deepseek", prompt),
                swarm.query_provider_cascade(client, "groq", prompt)
            ]
            
            responses = await asyncio.gather(*tasks)
            
            contributors = []
            consensus_parts = []
            
            for provider_name, (model, content) in zip(["deepseek", "groq"], responses):
                if model and content:
                    contributors.append(model)
                    consensus_parts.append(f"{provider_name.capitalize()}: {content}")
            
            if contributors:
                results.append({
                    "topic": topic,
                    "contributors": contributors,
                    "consensus": "\n\n".join(consensus_parts)
                })
    
    if results:
        out_dir = Path("jarvis_memory")
        out_dir.mkdir(exist_ok=True)
        ts = int(time.time())
        out_file = out_dir / f"bootstrap_{ts}.json"
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"Sauvegardé {len(results)} paires dans {out_file}")
        
        if notify_telegram:
            msg = f"🧠 <b>Jarvis Sovereign Neural Swarm a distillé {len(results)} étincelles d'innovation pure !</b>\n\nCascade exécutée avec succès.\nSauvegardé dans <code>{out_file}</code>."
            await send_telegram_message(msg)
            
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--notify-telegram", action="store_true")
    args = parser.parse_args()
    
    asyncio.run(run_swarm_bootstrap(args.n, args.notify_telegram))

if __name__ == "__main__":
    main()
