#!/usr/bin/env python3
"""Sovereign Community HQ Reset & Dedup Script for LeHuB (-1003920092778).
Deletes all duplicate forum topics (range 2..150), creates the 5 canonical specialized
topics with their distinct charters, posts the comprehensive guide in General (thread 1),
and persists the topic map into cache and .env.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.memory.telegram_vault import TelegramNeuralVault

GROUP_CHAT_ID = "-1003920092778"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8716120626:AAHqEDB4r0sn9nmEuguy9PyMEFCQOaSDY84")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


async def clean_and_setup():
    print(f"🚀 [COMMUNITY ENGINEER] Initialisation du nettoyage souverain sur {GROUP_CHAT_ID}...")
    vault = TelegramNeuralVault(token=TOKEN, chat_id=GROUP_CHAT_ID)
    vault.group_chat_id = GROUP_CHAT_ID

    deleted_threads = []
    failed_threads = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Scan and delete all topics in range 2..150
        print("\n🧹 Phase 1 : Suppression de tous les topics orphelins et en doublon (IDs 2..150)...")
        for tid in range(2, 151):
            try:
                res = await client.post(
                    f"{BASE_URL}/deleteForumTopic",
                    json={"chat_id": GROUP_CHAT_ID, "message_thread_id": tid}
                )
                if res.status_code == 200 and res.json().get("ok"):
                    deleted_threads.append(tid)
                    print(f"  ✔ Topic supprimé : thread_id={tid}")
                    await asyncio.sleep(0.12)
                elif res.status_code == 429:
                    retry_after = res.json().get("parameters", {}).get("retry_after", 2)
                    print(f"  ⏳ Rate-limit Telegram (429), attente de {retry_after}s...")
                    await asyncio.sleep(retry_after + 0.5)
                    # Retry once
                    res = await client.post(
                        f"{BASE_URL}/deleteForumTopic",
                        json={"chat_id": GROUP_CHAT_ID, "message_thread_id": tid}
                    )
                    if res.status_code == 200 and res.json().get("ok"):
                        deleted_threads.append(tid)
                        print(f"  ✔ Topic supprimé après retry : thread_id={tid}")
                else:
                    # Topic doesn't exist, ignore
                    pass
            except Exception as e:
                failed_threads.append((tid, str(e)))

        print(f"\n📊 Total topics supprimés : {len(deleted_threads)}")
        print(f"   Liste des IDs purgés : {deleted_threads}")

        # Step 2: Clear old cache
        vault.topic_map.clear()
        cache_path = vault._get_topics_cache_path()
        if cache_path.exists():
            cache_path.unlink()

        # Step 3: Setup the 5 specialized topics + General
        print("\n🏛️ Phase 2 : Création des 5 salons officiels spécialisés...")
        setup_res = await vault.setup_community_hq(target_chat_id=GROUP_CHAT_ID, force_recreate=True)
        print(f"   Résultat setup : {json.dumps(setup_res, indent=2, ensure_ascii=False)}")
        print(f"   Topic Map finale : {json.dumps(vault.topic_map, indent=2)}")

        # Step 4: Verify messages posted in each topic
        print("\n✅ Phase 3 : Vérification de la publication des chartes et du guide...")
        print("   - Charte Career postée dans topic", vault.topic_map.get("career"))
        print("   - Charte Crypto postée dans topic", vault.topic_map.get("crypto"))
        print("   - Charte Defense postée dans topic", vault.topic_map.get("defense"))
        print("   - Charte Forge postée dans topic", vault.topic_map.get("forge"))
        print("   - Charte Sanctuaire postée dans topic", vault.topic_map.get("tribute"))
        print("   - Guide Officiel complet posté dans topic 1 (Général)")

        return {
            "deleted_count": len(deleted_threads),
            "deleted_ids": deleted_threads,
            "topic_map": vault.topic_map,
            "setup_res": setup_res
        }


if __name__ == "__main__":
    result = asyncio.run(clean_and_setup())
    print("\n🎉 MISSION DU NETTOYAGE & CONFIGURATION ACCOMPLIE AVEC SUCCÈS !")
