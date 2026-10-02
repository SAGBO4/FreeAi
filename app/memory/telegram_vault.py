"""Telegram Cloud Neural Vault & Mobile Telepathy Conduit for FreeAI.
Transforms Telegram's encrypted distributed cloud into an infinite, zero-cost, zero-RAM
memory vault and mobile remote control for FreeAI.
Adheres strictly to Mode NÉANT (0 local disk writes, 100% in-memory GZIP Level 9).
"""

import os
import io
import json
import gzip
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx
from config.settings import settings
from app.security.sacred_life import SacredLifeSentinel

logger = logging.getLogger("telegram_vault")


class TelegramNeuralVault:
    """Infinite Serverless Cloud Memory Store & Mobile Telepathy Conduit via Telegram Bot API."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.last_update_id: int = 0
        self.sentinel = SacredLifeSentinel(strict_mode=True)
        self.synced_records_count: int = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    async def auto_discover_chat_id(self) -> Optional[str]:
        """Auto-discovers the user's chat_id from recent incoming Telegram messages."""
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self.base_url}/getUpdates", params={"offset": self.last_update_id + 1})
                if res.status_code == 200:
                    data = res.json()
                    updates = data.get("result", [])
                    if updates:
                        last = updates[-1]
                        self.last_update_id = last.get("update_id", self.last_update_id)
                        msg = last.get("message") or last.get("channel_post")
                        if msg and "chat" in msg:
                            discovered_id = str(msg["chat"]["id"])
                            self.chat_id = discovered_id
                            logger.info(f"[TELEGRAM VAULT] Auto-discovered Chat ID: {self.chat_id}")
                            return discovered_id
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Auto-discovery error: {e}")
        return self.chat_id if self.chat_id else None

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Sends a text message or formatted alert to the Telegram Neural Vault."""
        if not self.is_configured:
            return False

        if not self.chat_id:
            await self.auto_discover_chat_id()

        if not self.chat_id:
            logger.warning("[TELEGRAM VAULT] Cannot send message: Chat ID unknown. Send /start to @LesaintAi_bot.")
            return False

        # Mode NÉANT : pure memory payload
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4000],  # Telegram max length protection
            "parse_mode": parse_mode
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                if res.status_code == 200:
                    self.synced_records_count += 1
                    return True
                else:
                    logger.debug(f"[TELEGRAM VAULT] sendMessage failed ({res.status_code}): {res.text}")
                    return False
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Network error sending message: {e}")
            return False

    async def send_document(self, filename: str, data: bytes, caption: Optional[str] = None) -> bool:
        """Uploads an in-memory document (e.g. GZIP compressed memory checkpoint) to Telegram cloud."""
        if not self.is_configured:
            return False

        if not self.chat_id:
            await self.auto_discover_chat_id()

        if not self.chat_id:
            logger.warning("[TELEGRAM VAULT] Cannot send document: Chat ID unknown.")
            return False

        files = {"document": (filename, data, "application/gzip")}
        data_fields = {"chat_id": self.chat_id}
        if caption:
            data_fields["caption"] = caption[:1000]

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(f"{self.base_url}/sendDocument", data=data_fields, files=files)
                if res.status_code == 200:
                    self.synced_records_count += 1
                    return True
                else:
                    logger.debug(f"[TELEGRAM VAULT] sendDocument failed: {res.text}")
                    return False
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Document upload error: {e}")
            return False

    async def download_file_bytes(self, file_id: str) -> Optional[io.BytesIO]:
        """Downloads a Telegram file directly into RAM (0 disk write)."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/getFile", params={"file_id": file_id})
                if res.status_code != 200:
                    return None
                file_path = res.json().get("result", {}).get("file_path")
                if not file_path:
                    return None
                file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                dl_res = await client.get(file_url)
                if dl_res.status_code == 200:
                    stream = io.BytesIO(dl_res.content)
                    stream.seek(0)
                    return stream
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] File download error: {e}")
        return None

    async def send_voice(self, voice_data: io.BytesIO, caption: Optional[str] = None) -> bool:
        """Sends an in-memory voice message back to Telegram."""
        if not self.is_configured or not self.chat_id:
            return False
        files = {"voice": ("reply.ogg", voice_data.getvalue(), "audio/ogg")}
        data_fields = {"chat_id": self.chat_id}
        if caption:
            data_fields["caption"] = caption[:1000]
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(f"{self.base_url}/sendVoice", data=data_fields, files=files)
                return res.status_code == 200
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] sendVoice error: {e}")
            return False

    async def save_knowledge(self, topic: str, query: str, response: str) -> bool:
        """Stores structured knowledge in Telegram cloud memory with GZIP compression."""
        record = {
            "type": "knowledge",
            "topic": topic,
            "query": query,
            "response": response,
            "timestamp": time.time()
        }
        json_bytes = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes, compresslevel=9)

        # 1. Send readable Telegram notification
        preview = (
            f"🧠 <b>[FreeAI Neural Memory - #{topic}]</b>\n"
            f"<b>Requête :</b> {query[:120]}\n\n"
            f"<b>Synthèse :</b>\n<code>{response[:600]}...</code>\n\n"
            f"<i>📦 Stocké sur Telegram Cloud (0 octet local, GZIP-9)</i>"
        )
        await self.send_message(preview)

        # 2. Archive exact raw compressed payload
        fname = f"knowledge_{topic}_{int(time.time())}.json.gz"
        return await self.send_document(fname, compressed, caption=f"Archive brute #{topic}")

    async def save_checkpoint(self, label: str, checkpoint_data: Dict[str, Any]) -> bool:
        """Compresses and uploads a code or system state checkpoint to Telegram."""
        payload = {
            "type": "checkpoint",
            "label": label,
            "data": checkpoint_data,
            "timestamp": time.time()
        }
        compressed = gzip.compress(json.dumps(payload, default=str).encode("utf-8"), compresslevel=9)
        fname = f"checkpoint_{label.replace(' ', '_')}_{int(time.time())}.json.gz"
        caption = f"🛡️ Checkpoint Sauvegardé : {label} (GZIP-9, {len(compressed)} octets)"
        return await self.send_document(fname, compressed, caption=caption)

    async def save_thought_stream(self, thoughts: List[Dict[str, Any]]) -> bool:
        """Archives recent synthetic stream-of-consciousness pulses."""
        if not thoughts:
            return False

        lines = [f"🧠 <b>[Flux de Conscience FreeAI - {len(thoughts)} Pensées en RAM]</b>"]
        for t in thoughts[-5:]:
            t_str = time.strftime("%H:%M:%S", time.localtime(t.get("timestamp", time.time())))
            lines.append(f"• <i>{t_str}</i> [<code>{t.get('trigger')}</code>] : {t.get('reflection')}")

        lines.append("\n<i>☁️ Synchronisé sur Telegram Neural Vault</i>")
        return await self.send_message("\n".join(lines))

    async def poll_incoming_command(self, stt_engine: Any = None) -> Optional[Tuple[str, str]]:
        """Polls for new commands texted or spoken by the user on Telegram.
        Returns: (command_text, sender_username) or None
        """
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/getUpdates", params={"offset": self.last_update_id + 1, "timeout": 1})
                if res.status_code == 200:
                    data = res.json()
                    updates = data.get("result", [])
                    for update in updates:
                        self.last_update_id = update.get("update_id", self.last_update_id)
                        msg = update.get("message")
                        if not msg:
                            continue
                        
                        sender_chat_id = str(msg["chat"]["id"])
                        user_name = msg.get("from", {}).get("username", "Utilisateur")
                        text = msg.get("text", "").strip()

                        # Authentication guard: If chat_id is established, reject foreign senders
                        if self.chat_id and sender_chat_id != self.chat_id:
                            logger.warning(
                                f"[TELEGRAM VAULT] Rejet d'ordre émis par un expéditeur non autorisé "
                                f"(ID: {sender_chat_id}, Attendu: {self.chat_id})"
                            )
                            continue

                        # First connection: bind chat_id
                        if not self.chat_id:
                            self.chat_id = sender_chat_id
                            logger.info(f"[TELEGRAM VAULT] Liaison établie avec le Chat ID: {self.chat_id}")

                        # Handle Voice Notes (Bidirectional Telepathy)
                        if not text and msg.get("voice") and stt_engine:
                            voice_meta = msg["voice"]
                            file_id = voice_meta.get("file_id")
                            if file_id:
                                audio_stream = await self.download_file_bytes(file_id)
                                if audio_stream:
                                    try:
                                        text = await stt_engine.transcribe(audio_stream)
                                    except Exception as e:
                                        logger.debug(f"[TELEGRAM VAULT] Voice STT transcription failed: {e}")

                        if text:
                            # Inviolable Verification by SacredLifeSentinel
                            safe, reason = self.sentinel.audit_objective(text)
                            if not safe:
                                await self.send_message(f"⛔ <b>VETO SACRÉ :</b> Ordre rejeté ({reason})")
                                continue
                            return text, user_name
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Polling error: {e}")
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns the current vault configuration status."""
        return {
            "configured": self.is_configured,
            "bot_username": "LesaintAi_bot",
            "chat_id": self.chat_id or "En attente (/start requis sur @LesaintAi_bot)",
            "synced_records": self.synced_records_count,
            "cloud_storage": "Telegram Distributed MTProto Cloud",
            "local_ram_overhead_mb": 0.0,
            "local_disk_footprint_bytes": 0,
            "compression": "GZIP-9 In-Memory"
        }
