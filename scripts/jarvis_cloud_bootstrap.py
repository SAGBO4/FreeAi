import os
import time
import json
import asyncio
import httpx
import argparse
import random
from pathlib import Path

async def ask_model(client: httpx.AsyncClient, url: str, api_key: str, model: str, prompt: str) -> str:
    if not api_key:
        return ""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }
    try:
        res = await client.post(url, headers=headers, json=payload, timeout=20.0)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Erreur API {model}: {e}")
        return ""

async def send_telegram_message(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram non configuré.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Erreur Telegram: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--notify-telegram", action="store_true")
    args = parser.parse_args()

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

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

    selected_topics = [random.choice(topics) for _ in range(args.n)]
    results = []

    async with httpx.AsyncClient() as client:
        for i, topic in enumerate(selected_topics):
            print(f"[{i+1}/{args.n}] Sujet: {topic}")
            prompt = f"Génère une brève explication (3 phrases) très pointue sur le sujet suivant: {topic}. Ne mets pas de blabla introductif."
            
            task_ds = ask_model(client, "https://api.deepseek.com/chat/completions", deepseek_key, "deepseek-chat", prompt)
            # using mixtral on groq
            task_gr = ask_model(client, "https://api.groq.com/openai/v1/chat/completions", groq_key, "mixtral-8x7b-32768", prompt)
            
            res_ds, res_gr = await asyncio.gather(task_ds, task_gr)
            
            # Create a consensus if we got responses
            if res_ds or res_gr:
                consensus = f"DeepSeek: {res_ds}\n\nGroq: {res_gr}"
                results.append({
                    "topic": topic,
                    "deepseek": res_ds,
                    "groq": res_gr,
                    "consensus": consensus
                })
    
    if results:
        out_dir = Path("jarvis_memory")
        out_dir.mkdir(exist_ok=True)
        ts = int(time.time())
        out_file = out_dir / f"bootstrap_{ts}.json"
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"Sauvegardé {len(results)} paires dans {out_file}")
        
        if args.notify_telegram:
            msg = f"🧠 <b>Jarvis a appris {len(results)} nouvelles choses pendant ton sommeil !</b>\n\nGrâce au consensus Cloud (DeepSeek+Groq), les paires d'or ont été distillées.\nSauvegardé dans <code>{out_file}</code>."
            await send_telegram_message(msg)

if __name__ == "__main__":
    asyncio.run(main())
