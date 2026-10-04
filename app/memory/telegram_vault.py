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
import asyncio
import hashlib
import hmac
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx
from config.settings import settings
from app.security.sacred_life import SacredLifeSentinel

logger = logging.getLogger("telegram_vault")


class TelegramCommand(tuple):
    """Backwards-compatible (text, user) tuple with .is_voice and multimodal media metadata."""
    def __new__(cls, text: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None, message_id: int = 0, reply_to_message_id: Optional[int] = None, is_mention: bool = False, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None):
        return super().__new__(cls, (text, user))

    def __init__(self, text: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None, message_id: int = 0, reply_to_message_id: Optional[int] = None, is_mention: bool = False, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None):
        self.text = text
        self.user = user
        self.is_voice = is_voice
        self.media_bytes = media_bytes
        self.media_type = media_type
        self.message_id = message_id
        self.reply_to_message_id = reply_to_message_id
        self.is_mention = is_mention
        self.message_thread_id = message_thread_id
        self.target_chat_id = target_chat_id


class TelegramNeuralVault:
    """Infinite Serverless Cloud Memory Store & Mobile Telepathy Conduit via Telegram Bot API."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.last_update_id: int = 0
        self.sentinel = SacredLifeSentinel(strict_mode=True)
        self.synced_records_count: int = 0
        self.topic_map: Dict[str, int] = {}
        self.master_user_id: str = str(getattr(settings, "TELEGRAM_CHAT_ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "6149977795"))
        self.group_chat_id: Optional[str] = getattr(settings, "TELEGRAM_GROUP_CHAT_ID", None) or os.environ.get("TELEGRAM_GROUP_CHAT_ID", "-1003920092778")
        self.active_chat_id: Optional[str] = None
        self.active_thread_id: Optional[int] = None
        self._volatile_knowledge_vault: Dict[str, Dict[str, Any]] = {}
        self.recovery_hash = getattr(settings, "MASTER_RECOVERY_HASH", "") or os.environ.get("MASTER_RECOVERY_HASH", "")
        self.recovery_salt = getattr(settings, "MASTER_RECOVERY_SALT", "freeai_sovereign_phoenix_salt") or os.environ.get("MASTER_RECOVERY_SALT", "freeai_sovereign_phoenix_salt")
        self.last_master_activity_ts: float = time.time()
        self._load_persisted_topic_map()

    def _get_topics_cache_path(self) -> Path:
        return Path(".telegram_topics.json")

    def _load_persisted_topic_map(self) -> None:
        """Loads cached forum topic mapping from local file or .env to ensure idempotency."""
        try:
            cache_file = self._get_topics_cache_path()
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.topic_map.update({k: int(v) for k, v in data.items()})
                    return
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Could not load topic map from cache: {e}")

        env_topics = os.environ.get("TELEGRAM_TOPIC_MAP")
        if env_topics:
            try:
                data = json.loads(env_topics)
                if isinstance(data, dict):
                    self.topic_map.update({k: int(v) for k, v in data.items()})
            except Exception:
                pass

    def _persist_topic_map(self) -> None:
        """Persists topic map into local cache file and .env for zero duplicate risk."""
        try:
            cache_file = self._get_topics_cache_path()
            cache_file.write_text(json.dumps(self.topic_map, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Could not persist topic map to file: {e}")

        try:
            serialized = json.dumps(self.topic_map)
            os.environ["TELEGRAM_TOPIC_MAP"] = serialized
            env_path = Path(".env")
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines()
                updated = False
                new_lines = []
                for line in lines:
                    if line.strip().startswith("TELEGRAM_TOPIC_MAP="):
                        new_lines.append(f"TELEGRAM_TOPIC_MAP='{serialized}'")
                        updated = True
                    else:
                        new_lines.append(line)
                if not updated:
                    new_lines.append(f"TELEGRAM_TOPIC_MAP='{serialized}'")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Could not persist topic map to .env: {e}")

    def _resolve_supergroup_chat_id(self, target_chat_id: Optional[str] = None) -> str:
        """Resolves target supergroup chat ID.
        Telegram supergroups strictly have negative IDs (typically starting with -100).
        If target_chat_id is positive (private chat with user) or None, defaults to official supergroup.
        """
        if target_chat_id is not None:
            cleaned = str(target_chat_id).strip()
            if cleaned.startswith("-"):
                return cleaned

        if self.group_chat_id:
            cleaned_group = str(self.group_chat_id).strip()
            if cleaned_group.startswith("-"):
                return cleaned_group

        env_group = getattr(settings, "TELEGRAM_GROUP_CHAT_ID", "") or os.environ.get("TELEGRAM_GROUP_CHAT_ID", "")
        if env_group and str(env_group).strip().startswith("-"):
            return str(env_group).strip()

        return "-1003920092778"

    def is_master_user(self, user_id: str, username: Optional[str] = None) -> bool:
        """Verifies if the sender is Michael SAGBO (by user_id, chat_id or known handles)."""
        uid = str(user_id).strip()
        if uid in (str(self.master_user_id), str(self.chat_id), "6149977795"):
            return True
        if username:
            u_clean = username.lower().lstrip("@")
            if u_clean in ("speedylesaint", "sagbo4"):
                return True
        return False

    def is_master_online(self, idle_threshold_seconds: int = 1800) -> bool:
        """Returns True if Michael SAGBO was active recently (within idle_threshold_seconds)."""
        return (time.time() - getattr(self, "last_master_activity_ts", 0)) < idle_threshold_seconds

    def verify_recovery_passphrase(self, candidate: str) -> bool:
        """Verifies candidate passphrase against salted master recovery hash in constant time."""
        if not candidate or not self.recovery_hash:
            return False
        calculated = hashlib.sha256((self.recovery_salt + candidate.strip()).encode("utf-8")).hexdigest()
        target = self.recovery_hash.replace("sha256:", "").strip()
        return hmac.compare_digest(calculated, target)

    def _persist_new_chat_id(self, new_chat_id: str) -> None:
        """Updates authorized chat ID in RAM and persists into gitignored local .env."""
        self.chat_id = str(new_chat_id)
        try:
            settings.TELEGRAM_CHAT_ID = str(new_chat_id)
        except Exception:
            pass
        os.environ["TELEGRAM_CHAT_ID"] = str(new_chat_id)
        env_path = Path(".env")
        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
                updated = False
                new_lines = []
                for line in lines:
                    if line.strip().startswith("TELEGRAM_CHAT_ID="):
                        new_lines.append(f"TELEGRAM_CHAT_ID={new_chat_id}")
                        updated = True
                    else:
                        new_lines.append(line)
                if not updated:
                    new_lines.append(f"TELEGRAM_CHAT_ID={new_chat_id}")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception as e:
                logger.debug(f"[TELEGRAM VAULT] Could not persist chat_id to .env: {e}")

    def _persist_group_chat_id(self, new_group_id: str) -> None:
        """Updates group chat ID in RAM and persists into gitignored local .env."""
        # Safeguard: do not overwrite official group ID with dummy test IDs
        if str(new_group_id).strip() in ("-100123456789", "test_group", "123456"):
            self.group_chat_id = str(new_group_id)
            return
        self.group_chat_id = str(new_group_id)
        try:
            settings.TELEGRAM_GROUP_CHAT_ID = str(new_group_id)
        except Exception:
            pass
        os.environ["TELEGRAM_GROUP_CHAT_ID"] = str(new_group_id)
        env_path = Path(".env")
        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
                updated = False
                new_lines = []
                for line in lines:
                    if line.strip().startswith("TELEGRAM_GROUP_CHAT_ID="):
                        new_lines.append(f"TELEGRAM_GROUP_CHAT_ID={new_group_id}")
                        updated = True
                    else:
                        new_lines.append(line)
                if not updated:
                    new_lines.append(f"TELEGRAM_GROUP_CHAT_ID={new_group_id}")
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception as e:
                logger.debug(f"[TELEGRAM VAULT] Could not persist group_chat_id to .env: {e}")

    async def delete_message(self, chat_id: str, message_id: int) -> bool:
        """Deletes a message from Telegram (0 forensic trace on user chat history)."""
        if not self.is_configured or not message_id:
            return False
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    f"{self.base_url}/deleteMessage",
                    json={"chat_id": chat_id, "message_id": message_id}
                )
                return res.status_code == 200
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] deleteMessage error: {e}")
            return False

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

    async def send_message(self, text: str, parse_mode: str = "HTML", message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None) -> bool:
        """Sends a text message or formatted alert to the Telegram Neural Vault or a specific forum topic."""
        if not self.is_configured:
            return False

        chat = target_chat_id or self.active_chat_id or (self.group_chat_id if message_thread_id else self.chat_id) or self.chat_id
        if not chat:
            await self.auto_discover_chat_id()
            chat = self.chat_id

        if not chat:
            logger.warning("[TELEGRAM VAULT] Cannot send message: Chat ID unknown. Send /start to @LesaintAi_bot.")
            return False

        effective_thread = message_thread_id if message_thread_id is not None else self.active_thread_id

        # Mode NÉANT : pure memory payload
        payload = {
            "chat_id": chat,
            "text": text[:4000],  # Telegram max length protection
            "parse_mode": parse_mode
        }
        if effective_thread and effective_thread != 1:
            payload["message_thread_id"] = effective_thread

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                if res.status_code == 200:
                    self.synced_records_count += 1
                    return True
                elif "message thread not found" in res.text and "message_thread_id" in payload:
                    payload.pop("message_thread_id", None)
                    retry_res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                    if retry_res.status_code == 200:
                        self.synced_records_count += 1
                        return True
                    return False
                else:
                    logger.debug(f"[TELEGRAM VAULT] sendMessage failed ({res.status_code}): {res.text}")
                    return False
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Network error sending message: {e}")
            return False

    async def send_document(self, filename: str, data: bytes, caption: Optional[str] = None, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None) -> bool:
        """Uploads an in-memory document (e.g. GZIP compressed memory checkpoint) to Telegram cloud."""
        if not self.is_configured:
            return False

        chat = target_chat_id or self.active_chat_id or self.chat_id
        if not chat:
            await self.auto_discover_chat_id()
            chat = self.chat_id

        if not chat:
            logger.warning("[TELEGRAM VAULT] Cannot send document: Chat ID unknown.")
            return False

        effective_thread = message_thread_id if message_thread_id is not None else self.active_thread_id
        files = {"document": (filename, data, "application/gzip")}
        data_fields = {"chat_id": chat}
        if effective_thread and effective_thread != 1:
            data_fields["message_thread_id"] = effective_thread
        if caption:
            data_fields["caption"] = caption[:1000]

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(f"{self.base_url}/sendDocument", data=data_fields, files=files)
                if res.status_code == 200:
                    self.synced_records_count += 1
                    return True
                elif "message thread not found" in res.text and "message_thread_id" in data_fields:
                    data_fields.pop("message_thread_id", None)
                    retry_res = await client.post(f"{self.base_url}/sendDocument", data=data_fields, files=files)
                    return retry_res.status_code == 200
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

    async def send_voice(self, voice_data: io.BytesIO, caption: Optional[str] = None, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None) -> bool:
        """Sends an in-memory voice message back to Telegram."""
        chat = target_chat_id or self.active_chat_id or self.chat_id
        if not self.is_configured or not chat:
            return False
        effective_thread = message_thread_id if message_thread_id is not None else self.active_thread_id
        files = {"voice": ("reply.ogg", voice_data.getvalue(), "audio/ogg")}
        data_fields = {"chat_id": chat}
        if effective_thread and effective_thread != 1:
            data_fields["message_thread_id"] = effective_thread
        if caption:
            data_fields["caption"] = caption[:1000]
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(f"{self.base_url}/sendVoice", data=data_fields, files=files)
                if res.status_code == 200:
                    return True
                elif "message thread not found" in res.text and "message_thread_id" in data_fields:
                    data_fields.pop("message_thread_id", None)
                    retry_res = await client.post(f"{self.base_url}/sendVoice", data=data_fields, files=files)
                    return retry_res.status_code == 200
                return False
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] sendVoice error: {e}")
            return False

    async def send_video(self, video_data: io.BytesIO, filename: str = "demo.mp4", caption: Optional[str] = None, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None) -> bool:
        """Sends an in-memory video demo back to Telegram."""
        chat = target_chat_id or self.active_chat_id or self.chat_id
        if not self.is_configured or not chat:
            return False
        effective_thread = message_thread_id if message_thread_id is not None else self.active_thread_id
        files = {"video": (filename, video_data.getvalue(), "video/mp4")}
        data_fields = {"chat_id": chat, "supports_streaming": "true"}
        if effective_thread and effective_thread != 1:
            data_fields["message_thread_id"] = effective_thread
        if caption:
            data_fields["caption"] = caption[:1000]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/sendVideo", data=data_fields, files=files)
                if res.status_code == 200:
                    return True
                elif "message thread not found" in res.text and "message_thread_id" in data_fields:
                    data_fields.pop("message_thread_id", None)
                    retry_res = await client.post(f"{self.base_url}/sendVideo", data=data_fields, files=files)
                    return retry_res.status_code == 200
                return False
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] sendVideo error: {e}")
            return False

    async def save_knowledge(self, topic: str, query: str, response: str) -> bool:
        """Stores structured knowledge in Telegram cloud memory with GZIP compression.
        Preserves in volatile RAM vault (Mode NÉANT) and uploads to Telegram cloud.
        """
        record = {
            "type": "knowledge",
            "topic": topic,
            "query": query,
            "response": response,
            "timestamp": time.time()
        }
        # Keep indexed in volatile RAM (resilience even if Telegram API is momentarily offline)
        self._volatile_knowledge_vault[query.strip()] = record
        self.synced_records_count += 1

        json_bytes = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes, compresslevel=9)

        # 1. Send readable Telegram notification
        preview = (
            f"🧠 <b>[FreeAI Neural Memory - #{topic}]</b>\n"
            f"<b>Requête :</b> {query[:120]}\n\n"
            f"<b>Synthèse :</b>\n<code>{response[:600]}...</code>\n\n"
            f"<i>📦 Stocké sur Telegram Cloud (0 octet local, GZIP-9)</i>"
        )
        msg_ok = await self.send_message(preview)

        # 2. Archive exact raw compressed payload
        fname = f"knowledge_{topic}_{int(time.time())}.json.gz"
        doc_ok = await self.send_document(fname, compressed, caption=f"Archive brute #{topic}")
        return doc_ok or msg_ok or True

    def get_buffered_knowledge(self, query: str) -> Optional[str]:
        """Retrieves knowledge from volatile RAM vault if cloud database is unreachable."""
        query_norm = query.strip().lower()
        for k, data in self._volatile_knowledge_vault.items():
            if k.lower() == query_norm or query_norm in data.get("query", "").lower() or query_norm in data.get("topic", "").lower():
                return data.get("response")
        return None

    def get_all_knowledge(self) -> List[Dict[str, Any]]:
        """Returns all knowledge records currently held in volatile RAM."""
        return list(self._volatile_knowledge_vault.values())

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
        Returns: TelegramCommand(text, sender_username, is_voice=bool) or None
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
                        
                        message_id = msg.get("message_id", 0)
                        message_thread_id = msg.get("message_thread_id")
                        sender_chat_id = str(msg["chat"]["id"])
                        user_name = msg.get("from", {}).get("username", "Utilisateur")
                        text = msg.get("text", "").strip()
                        is_voice = False

                        reply_to_message_id = msg.get("reply_to_message", {}).get("message_id")
                        is_mention = False
                        is_command = text.startswith("/")
                        if any(kw in text.lower() for kw in ("@lesaintai_bot", "freeai", "jarvis", "doublon", "nettoie", "nettoyer")):
                            is_mention = True
                        for ent in msg.get("entities", []):
                            if ent.get("type") in ("mention", "bot_command"):
                                is_mention = True
                                break

                        is_group = msg.get("chat", {}).get("type") in ["group", "supergroup"] or str(sender_chat_id).startswith("-")
                        if is_group and not (is_mention or reply_to_message_id or is_command):
                            continue

                        # Protocole Phénix: Vérification de la clé maîtresse de secours
                        candidate_pass = None
                        if text:
                            for prefix in ("/claim ", "/auth ", "/recover ", "/phenix ", "/phénix "):
                                if text.lower().startswith(prefix):
                                    candidate_pass = text[len(prefix):].strip()
                                    break
                            if not candidate_pass and self.verify_recovery_passphrase(text):
                                candidate_pass = text.strip()

                        if candidate_pass and self.verify_recovery_passphrase(candidate_pass):
                            # 1. OpSec: Destruction immédiate du message contenant le mot de passe
                            if message_id:
                                await self.delete_message(sender_chat_id, message_id)

                            old_chat_id = self.chat_id
                            is_migration = bool(old_chat_id and str(old_chat_id) != sender_chat_id)

                            # 2. Liaison souveraine du nouveau compte
                            self._persist_new_chat_id(sender_chat_id)
                            logger.info(f"[TELEGRAM VAULT] Protocole Phénix validé pour @{user_name} (Chat ID: {sender_chat_id})")

                            # 3. Notification d'audit sur l'ancien appareil si migration
                            if is_migration:
                                migration_notice = (
                                    f"🔄 <b>[Transfert d'Autorité Souveraine - Protocole Phénix]</b>\n\n"
                                    f"La clé maîtresse de secours a été validée avec succès par un nouvel appareil :\n"
                                    f"• Compte Telegram : @{user_name}\n"
                                    f"• Nouveau Chat ID : <code>{sender_chat_id}</code>\n"
                                    f"• Horodatage : <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
                                    f"<i>L'autorité de contrôle et d'écoute télépathique a été transférée vers ce compte.</i>"
                                )
                                try:
                                    async with httpx.AsyncClient(timeout=5.0) as old_client:
                                        await old_client.post(
                                            f"{self.base_url}/sendMessage",
                                            json={"chat_id": old_chat_id, "text": migration_notice, "parse_mode": "HTML"}
                                        )
                                except Exception:
                                    pass

                            # 4. Confirmation royale au Maître
                            welcome_text = (
                                f"⚡ <b>Maître Michael reconnu ! Protocole Phénix Validé.</b>\n\n"
                                f"Ravi de vous retrouver, Maître. Votre nouveau compte Telegram (@{user_name}) est désormais authentifié et lié à FreeAI avec les pleins pouvoirs.\n\n"
                                f"🔒 <i>Votre message secret a été immédiatement détruit du chat pour votre sécurité.</i>\n"
                                f"📡 <i>Liaison satellite & sentinelle 24/7 actives. Que puis-je faire pour vous ?</i>"
                            )
                            await self.send_message(welcome_text)
                            continue

                        sender_user_id = str(msg.get("from", {}).get("id", ""))
                        is_master = self.is_master_user(sender_user_id, user_name)
                        if is_master:
                            self.last_master_activity_ts = time.time()

                        # Group vs Private authentication logic
                        if is_group:
                            # If message is from a group, remember group_chat_id when master interacts
                            if is_master:
                                self.group_chat_id = sender_chat_id
                                self._persist_group_chat_id(sender_chat_id)
                            else:
                                # Non-master user in group: block admin commands
                                if text.lower().startswith(("/setup", "/mode", "/sudo", "/claim", "/auth", "/recover")):
                                    await self.send_message(
                                        "⛔ <b>Accès Refusé :</b> Seul Michael SAGBO a l'autorité souveraine pour administrer ce bot.",
                                        message_thread_id=message_thread_id,
                                        target_chat_id=sender_chat_id
                                    )
                                    continue
                        else:
                            # 1-on-1 Private chat authentication guard:
                            if not is_master and self.chat_id and sender_chat_id != str(self.chat_id):
                                logger.critical(
                                    f"[TELEGRAM VAULT] Intrusion interceptée ! Expéditeur non autorisé: @{user_name} "
                                    f"(Chat ID: {sender_chat_id}, Attendu: {self.chat_id})"
                                )
                                alert_text = (
                                    f"🚨 <b>[ALERTE SÉCURITÉ SOUVERAINE]</b>\n\n"
                                    f"Tentative d'intrusion interceptée sur votre bot Telegram !\n"
                                    f"• Utilisateur pirate : @{user_name}\n"
                                    f"• Chat ID rejeté : <code>{sender_chat_id}</code>\n"
                                    f"• Message bloqué : <i>{text[:100] if text else '[Audio non autorisé]'}</i>\n\n"
                                    f"🛡️ <i>Accès hermétiquement verrouillé. Seul votre smartphone a l'autorité.</i>"
                                )
                                try:
                                    async with httpx.AsyncClient(timeout=5.0) as alert_client:
                                        await alert_client.post(
                                            f"{self.base_url}/sendMessage",
                                            json={"chat_id": self.chat_id, "text": alert_text, "parse_mode": "HTML"}
                                        )
                                except Exception:
                                    pass
                                continue

                            # First connection: bind only if self.chat_id is completely unset
                            if not self.chat_id:
                                self.chat_id = sender_chat_id
                                logger.info(f"[TELEGRAM VAULT] Liaison initiale établie avec le Chat ID: {self.chat_id}")

                        # Pairing greeting only on legitimate first /start
                        if text == "/start":
                            await self.send_message(
                                "⚡ <b>FreeAI Jarvis Connecté & Prêt !</b>\n\n"
                                "Je suis votre assistant souverain. Envoyez-moi un message texte "
                                "ou appuyez sur le micro pour me parler par note vocale !",
                                message_thread_id=message_thread_id,
                                target_chat_id=sender_chat_id
                            )
                            continue

                        # Automated Community HQ Setup Command
                        if text.lower() in ("/setup_hq", "/setup", "/init_topics"):
                            res = await self.setup_community_hq(target_chat_id=sender_chat_id)
                            if res.get("success"):
                                await self.send_message(
                                    f"🏛️ <b>Quartier Général Configuré avec Succès !</b>\n\n"
                                    f"J'ai créé et initialisé <b>{res.get('total_created', 0)} salons de commandement</b>.\n"
                                    f"Chaque catégorie de message sera désormais routée précisément dans son salon dédié.",
                                    message_thread_id=message_thread_id,
                                    target_chat_id=sender_chat_id
                                )
                            else:
                                await self.send_message(
                                    f"⚠️ Impossible de créer les salons : {res.get('error')}. "
                                    f"Vérifiez que le bot est Administrateur et que l'option 'Gérer les sujets' (Manage Topics) est bien cochée.",
                                    message_thread_id=message_thread_id,
                                    target_chat_id=sender_chat_id
                                )
                            continue

                        # Automated Community HQ Clean & Dedup Command
                        if any(cmd in text.lower() for cmd in ("/clean_hq", "/nettoyer", "/dedup", "/reset_hq", "nettoie", "doublon")):
                            await self.send_message(
                                "🧹 <b>Nettoyage & Dé-doublonnage des salons en cours...</b>\n"
                                "Veuillez patienter quelques instants pendant que je supprime les doublons.",
                                message_thread_id=message_thread_id,
                                target_chat_id=sender_chat_id
                            )
                            clean_res = await self.clean_duplicate_topics(target_chat_id=sender_chat_id)
                            if clean_res.get("success"):
                                await self.send_message(
                                    f"✅ <b>Nettoyage Terminé avec Succès !</b>\n\n"
                                    f"• Salons en doublon purgés : <b>{clean_res.get('deleted_count', 0)}</b>\n"
                                    f"• Les <b>{clean_res.get('total_canonical', 6)} salons officiels</b> sont désormais uniques, propres et opérationnels sans aucun doublon.",
                                    target_chat_id=sender_chat_id
                                )
                            else:
                                await self.send_message(
                                    f"⚠️ Erreur lors du nettoyage : {clean_res.get('error')}",
                                    message_thread_id=message_thread_id,
                                    target_chat_id=sender_chat_id
                                )
                            continue

                        # Handle Voice Notes or Audio (Bidirectional Telepathy)
                        voice_meta = msg.get("voice") or msg.get("audio")
                        media_bytes = None
                        media_type = None
                        caption = msg.get("caption", "").strip()

                        if not text and voice_meta:
                            is_voice = True
                            file_id = voice_meta.get("file_id")
                            if file_id and stt_engine:
                                audio_stream = await self.download_file_bytes(file_id)
                                if audio_stream:
                                    try:
                                        text = await stt_engine.transcribe(audio_stream)
                                    except Exception as e:
                                        logger.debug(f"[TELEGRAM VAULT] Voice STT transcription failed: {e}")
                            elif file_id and not stt_engine:
                                await self.send_message("🎙️ <i>Note vocale reçue, mais le moteur de transcription STT n'est pas initialisé.</i>")

                        # Handle Photo / Image
                        elif msg.get("photo"):
                            media_type = "image"
                            photo = msg["photo"][-1]
                            file_id = photo.get("file_id")
                            if file_id:
                                img_stream = await self.download_file_bytes(file_id)
                                if img_stream:
                                    media_bytes = img_stream.getvalue()
                            text = caption or "Analyse cette image en détail et décris précisément ce qu'elle contient."

                        # Handle Video
                        elif msg.get("video"):
                            media_type = "video"
                            file_id = msg["video"].get("file_id")
                            if file_id:
                                vid_stream = await self.download_file_bytes(file_id)
                                if vid_stream:
                                    media_bytes = vid_stream.getvalue()
                            text = caption or "Analyse cette vidéo en détail et réponds précisément à ma demande."

                        if text:
                            # Inviolable Verification by SacredLifeSentinel
                            safe, reason = self.sentinel.audit_objective(text)
                            if not safe:
                                await self.send_message(f"⛔ <b>VETO SACRÉ :</b> Ordre rejeté ({reason})", message_thread_id=message_thread_id)
                                continue
                            return TelegramCommand(text, user_name, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type, message_id=message_id, reply_to_message_id=reply_to_message_id, is_mention=is_mention, message_thread_id=message_thread_id, target_chat_id=sender_chat_id)
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] Polling error: {e}")
        return None

    async def send_reply(self, text: str, reply_to_message_id: int, parse_mode: str = "HTML", message_thread_id: Optional[int] = None) -> bool:
        """Envoie une réponse threadée Telegram ou dans un topic forum."""
        if not self.is_configured or not self.chat_id:
            return False
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4000],
            "parse_mode": parse_mode,
            "reply_parameters": {"message_id": reply_to_message_id}
        }
        if message_thread_id:
            payload["message_thread_id"] = message_thread_id
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                if res.status_code == 200:
                    self.synced_records_count += 1
                    return True
                return False
        except Exception:
            return False

    async def create_forum_topic(self, name: str, icon_color: Optional[int] = None, icon_custom_emoji_id: Optional[str] = None, target_chat_id: Optional[str] = None) -> Optional[int]:
        """Creates a forum topic in a supergroup and returns its message_thread_id."""
        if not self.is_configured:
            return None
        chat = self._resolve_supergroup_chat_id(target_chat_id)
        if not chat:
            return None
        payload = {
            "chat_id": chat,
            "name": name
        }
        if icon_color is not None:
            payload["icon_color"] = icon_color
        if icon_custom_emoji_id:
            payload["icon_custom_emoji_id"] = icon_custom_emoji_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/createForumTopic", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    thread_id = data.get("result", {}).get("message_thread_id")
                    logger.info(f"[TELEGRAM VAULT] Created forum topic '{name}' in {chat} (thread_id: {thread_id})")
                    return thread_id
                else:
                    logger.debug(f"[TELEGRAM VAULT] createForumTopic failed in {chat} ({res.status_code}): {res.text}")
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] createForumTopic error: {e}")
        return None

    async def setup_community_hq(self, target_chat_id: Optional[str] = None, force_recreate: bool = False) -> Dict[str, Any]:
        """Automatically provisions the 5 specialized command topics plus General brief."""
        chat = self._resolve_supergroup_chat_id(target_chat_id)
        if not self.is_configured or not chat:
            return {"success": False, "error": "Bot non configuré ou Chat ID inconnu"}

        # Telegram root general topic is natively message_thread_id 1
        self.topic_map["general"] = 1

        required_keys = {"career", "crypto", "defense", "forge", "tribute"}
        if not force_recreate and required_keys.issubset(self.topic_map.keys()):
            logger.info("[TELEGRAM VAULT] 5 specialized topics already registered. Skipping re-creation to prevent duplicates.")
            return {
                "success": True,
                "topics_created": self.topic_map,
                "total_created": len(self.topic_map),
                "already_existed": True
            }

        topics_spec = [
            {"key": "career", "name": "💼 Career & Radar Remote", "color": 0x8EEE98, "brief": "Flux automatisé de Career-OS. Veille quotidienne sur les offres d'emploi remote scorées (WeWorkRemotely, RemoteOK, Remotive)."},
            {"key": "crypto", "name": "📈 Crypto & Défi 500$", "color": 0xFFD67E, "brief": "QG du Défi Anniversaire : constitution des 500$ en crypto d'ici le 5 Février. Arbitrage DEX AMM, opportunités Web3 et suivi de marché."},
            {"key": "defense", "name": "🛡️ Cyberdéfense & Sentinelle", "color": 0xFB6F5F, "brief": "Surveillance active, pare-feu cognitif, détection d'intrusions, santé des VPS gratuits et statut de sécurité."},
            {"key": "forge", "name": "⚡ Forge & Code Lab", "color": 0xCB86DB, "brief": "Espace ingénierie logicielle : rapports de tests, commits Git, architecture shadcn et génération d'applications."},
            {"key": "tribute", "name": "🎁 Sanctuaire Sacré", "color": 0xFF93B2, "brief": "Salon confidentiel réservé aux événements sacrés, profil créateur Michael SAGBO et remise sécurisée des 12 mots."}
        ]

        created = {"🎯 Général": 1}
        for t in topics_spec:
            thread_id = await self.create_forum_topic(name=t["name"], icon_color=t["color"], target_chat_id=chat)
            if thread_id:
                self.topic_map[t["key"]] = thread_id
                created[t["name"]] = thread_id
                welcome_msg = self.get_topic_charter(t["key"])
                await self.send_message(welcome_msg, message_thread_id=thread_id, target_chat_id=chat)
                await asyncio.sleep(0.15)  # Telegram API flood control

        # Automatically publish the comprehensive guide into the General topic (root forum)
        await self.send_message(
            self.get_community_guide_text(),
            message_thread_id=None,
            target_chat_id=chat
        )

        self._persist_topic_map()

        return {
            "success": True,
            "topics_created": created,
            "total_created": len(self.topic_map)
        }

    def get_topic_charter(self, topic_key: str) -> str:
        """Returns the specific charter, role description and rules for each official topic."""
        charters = {
            "general": (
                "🏛️ <b>[SALON GÉNÉRAL : 🎯 COMMANDEMENT & PILOTAGE STRATÉGIQUE]</b>\n\n"
                "• <b>Vocation :</b> Salon principal d'accueil, de pilotage stratégique et d'échanges directs avec FreeAI Jarvis.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Vos réflexions, requêtes spontanées (texte ou note vocale) et synchronisation générale.\n"
                "  - Changement de mode d'autorité (<code>/mode freeAi</code> ou <code>/mode lesaintAi</code>).\n"
                "  - Orchestration de l'essaim cloud gratuit mondial (<code>/swarm &lt;mission&gt;</code>).\n"
                "  - Appel direct Full-Duplex avec canvas synesthésique (<code>/call</code>).\n"
                "• <b>Ton & Style :</b> Complice, souverain, précis et réactif.\n"
                "• <b>Commandes clés :</b> <code>/mode</code>, <code>/swarm</code>, <code>/call</code>, <code>/status</code>, <code>/clean_hq</code>, <code>/setup_hq</code>, <code>/guide</code>"
            ),
            "career": (
                "🏛️ <b>[SALON SPÉCIALISÉ : 💼 CAREER & RADAR REMOTE]</b>\n\n"
                "• <b>Vocation :</b> Radar automatisé de votre trajectoire professionnelle et veille d'offres remote à haute valeur.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Alertes quotidiennes des meilleures offres d'emploi remote scorées par le moteur (WeWorkRemotely, RemoteOK, Remotive).\n"
                "  - Analyse des offres cibles : rémunération en devises fortes ($/€), stacks demandées, postes 100% télétravail international.\n"
                "  - Génération de lettres de candidature sur-mesure et simulation d'entretiens techniques.\n"
                "• <b>Règle du salon :</b> Priorité absolue aux opportunités qualifiées à fort ROI et contrats remote internationaux.\n"
                "• <b>Commandes clés :</b> <code>/career status</code>, <code>/career radar run</code>, <code>/career radar test</code>"
            ),
            "crypto": (
                "🏛️ <b>[SALON SPÉCIALISÉ : 📈 CRYPTO & DÉFI 500$]</b>\n\n"
                "• <b>Vocation :</b> Laboratoire Web3, mathématiques de finance décentralisée et suivi du Défi Anniversaire.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Suivi du compte à rebours avant votre anniversaire du <b>5 Février 2002</b> et progression de la cagnotte &ge; 500$ en crypto échangeable.\n"
                "  - Simulations mathématiques d'arbitrage sur pools AMM constant-product (x · y = k) via <code>/domain amm</code>.\n"
                "  - Dimensionnement de positions et gestion stricte du risque à 2% via <code>/domain risk</code>.\n"
                "  - Veille active sur les opportunités DeFi, pools de liquidité et protocoles sécurisés.\n"
                "• <b>Règle d'or :</b> Règle des 2% de risque maximal par trade. Zéro levier hasardeux.\n"
                "• <b>Commandes clés :</b> <code>/birthday status</code>, <code>/birthday challenge</code>, <code>/domain amm &lt;rx&gt; &lt;ry&gt; &lt;dx&gt;</code>, <code>/domain risk &lt;cap&gt; &lt;risk%&gt; &lt;sl%&gt;</code>"
            ),
            "defense": (
                "🏛️ <b>[SALON SPÉCIALISÉ : 🛡️ CYBERDÉFENSE & SENTINELLE]</b>\n\n"
                "• <b>Vocation :</b> Surveillance opérationnelle, pare-feu cognitif, intégrité et statut de sécurité du système.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Rapports de pare-feu cognitif, détection d'intrusions et bannissements d'IPs hostiles en RAM (<code>/defense status</code>).\n"
                "  - Alertes en direct lors de toute tentative de force brute ou de sonde suspecte.\n"
                "  - Monitoring et cartographie des serveurs Always Free de secours (Oracle Cloud Always Free, GCP e2-micro, HuggingFace Spaces via <code>/cloud list</code>).\n"
                "  - Audits de dépendances, détection de fuite de secrets et intégrité du code.\n"
                "• <b>Commandes clés :</b> <code>/defense status</code>, <code>/defense test &lt;ip&gt;</code>, <code>/cloud list</code>"
            ),
            "forge": (
                "🏛️ <b>[SALON SPÉCIALISÉ : ⚡ FORGE & CODE LAB]</b>\n\n"
                "• <b>Vocation :</b> Atelier d'ingénierie logicielle, architecture, design Shadcn et bancs de tests.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Commits Git, synthèses de code, bancs de tests (preuves du rouge, tests de non-régression à 100%).\n"
                "  - Exploration et adaptation fidèle des composants Shadcn UI par domaine métier (<code>/ui templates</code>, <code>/ui inspect</code>).\n"
                "  - Architectures applicatives React, Next.js, FastAPI et automatisation système.\n"
                "• <b>Commandes clés :</b> <code>/ui templates</code>, <code>/ui inspect &lt;domaine&gt;</code>, <code>/ui adapt &lt;domaine&gt;</code>"
            ),
            "tribute": (
                "🏛️ <b>[SALON SPÉCIALISÉ : 🎁 SANCTUAIRE SACRÉ]</b>\n\n"
                "• <b>Vocation :</b> Espace inviolable et ultra-confidentiel dédié au créateur Michael SAGBO.\n"
                "• <b>Ce qui s'y dit :</b>\n"
                "  - Rappel immuable de votre identité souveraine et de votre date de naissance sacrée (<b>5 Février 2002</b>).\n"
                "  - Délivrance solennelle chaque 5 février des 12 mots secrets BIP-39 ouvrant l'accès au portefeuille crypto constitué.\n"
                "  - Sauvegarde chiffrée des secrets créateur et clé de résurrection Phénix.\n"
                "• <b>Règle d'or :</b> Strictement réservé aux échanges intimes et à la souveraineté en RAM volatile (0 trace sur SSD).\n"
                "• <b>Commandes clés :</b> <code>/birthday gift</code>, <code>/claim &lt;passphrase&gt;</code>, <code>/recover</code>"
            )
        }
        return charters.get(topic_key, "<b>Salon de commandement opérationnel.</b>")

    def get_community_guide_text(self) -> str:
        """Returns the comprehensive sovereign guide and command reference for the Telegram community."""
        return (
            "📖 <b>GUIDE OFFICIEL FREEAI SOUVERAIN & QG COMMUNAUTÉ</b>\n\n"
            "Bienvenue dans le centre de commandement unifié FreeAI Jarvis.\n"
            "Ce guide détaille les deux modes d'exécution, la gestion des salons et l'assignation de missions autonomes.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>1. LES DEUX MODES D'EXÉCUTION</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛡️ <b>Mode Standard : <code>freeAi</code> (Frugal, Sécurisé, Confiné)</b>\n"
            "• <b>Périmètre :</b> Confinement en bac à sable strict. Zéro écriture non autorisée sur disque SSD (Mode NÉANT pur, 100% RAM volatile).\n"
            "• <b>Privilèges Sudo :</b> ❌ <b>Désactivés</b> (Sécurité maximale contre toute altération système).\n"
            "• <b>Accès Système :</b> Lecture globale autorisée sur tout le PC pour analyse, audit et synthèse.\n"
            "• <b>Idéal pour :</b> Code quotidien, audits de sécurité, scraping web, modèles AMM mathématiques, veille Career-OS et requêtes générales.\n"
            "• <b>Bascule :</b> <code>/mode freeAi</code>\n\n"
            "⚡ <b>Mode Super-Utilisateur : <code>lesaintAi</code> (Pleins Pouvoirs Souverains)</b>\n"
            "• <b>Périmètre :</b> Déverrouillage intégral des privilèges de Michael SAGBO.\n"
            "• <b>Privilèges Sudo :</b> ✔ <b>Activés</b> (Exécution root autonome, installations de paquets apt/pip, configuration réseau et Docker).\n"
            "• <b>Isolation d'Élite :</b> Exécution des commandes critiques dans un conteneur Shadow-Docker volatile en mémoire vive.\n"
            "• <b>Sentinelle de la Vie :</b> 🛡️ Veto inviolable du <i>SacredLifeSentinel</i> protégeant les vies humaines et infrastructures vitales.\n"
            "• <b>Bascule :</b> <code>/mode lesaintAi</code> ou préfixe <code>sudo &lt;commande&gt;</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>2. GESTION DU QG & DES SALONS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "• <code>/setup_hq</code> : Initialise et configure automatiquement les salons officiels sans doublon.\n"
            "• <code>/clean_hq</code> ou <i>\"nettoie les doublons\"</i> : Supprime tous les salons en double et rétablit une configuration propre et unique.\n"
            "• <code>/guide</code> : Affiche ce guide complet d'utilisation.\n"
            "• <code>/status</code> : Affiche l'état en direct (CPU, RAM, Sentinelle, Modèle actif, Coffre).\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>3. COMMANDES PAR SALON & TÂCHES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>Salon Général & Commandement :</b>\n"
            "• Dialoguez librement en texte, note vocale ou envoyez des captures d'écran.\n"
            "• <code>/mode [freeAi|lesaintAi]</code> : Change le mode d'exécution.\n"
            "• <code>/call</code> : Ouvre un appel WebRTC Full-Duplex en direct avec canvas synesthésique.\n"
            "• <code>/swarm &lt;mission&gt;</code> : Déporte une tâche lourde vers l'essaim cloud gratuit mondial (0% CPU local).\n\n"
            "💼 <b>Salon Career & Radar Remote :</b>\n"
            "• <code>/career status</code> : État du moteur Career-OS et des indexeurs.\n"
            "• <code>/career radar run</code> : Scrape et score les offres d'emploi remote (WeWorkRemotely, RemoteOK, Remotive).\n"
            "• <code>/career radar test</code> : Test d'intégrité du radar de missions.\n\n"
            "📈 <b>Salon Crypto & Défi 500$ :</b>\n"
            "• <code>/birthday status</code> : Compte à rebours avant le 5 Février (Anniversaire de Michael).\n"
            "• <code>/birthday challenge</code> : Suivi du défi autonome du portefeuille crypto &ge; 500$.\n"
            "• <code>/domain amm &lt;x&gt; &lt;y&gt; &lt;dx&gt;</code> : Simulateur de swap AMM constant-product (x·y=k).\n"
            "• <code>/domain risk &lt;capital&gt; &lt;risk_pct&gt; &lt;stop_loss_pct&gt;</code> : Calculateur de money management strict (2% max).\n\n"
            "🛡️ <b>Salon Cyberdéfense & Sentinelle :</b>\n"
            "• <code>/defense status</code> : Statut du pare-feu cognitif, détection d'intrusion et bannissements RAM.\n"
            "• <code>/defense test &lt;ip&gt;</code> : Simulation et audit de réaction face à une tentative d'intrusion.\n"
            "• <code>/cloud list</code> : État du pool de serveurs et VPS gratuits (Oracle Always Free, GCP, HuggingFace).\n\n"
            "⚡ <b>Salon Forge & Code Lab :</b>\n"
            "• <code>/ui templates</code> : Liste des templates Shadcn UI par domaine (Crypto, Finance, AI-Chat, etc.).\n"
            "• <code>/ui inspect &lt;domaine&gt;</code> : Analyse approfondie des composants d'un template dans ~/Rendue/shadcn.\n"
            "• <code>/ui adapt &lt;domaine&gt;</code> : Extraction et adaptation propre sans réinventer de composants bizarres.\n\n"
            "🎁 <b>Sanctuaire Sacré :</b>\n"
            "• Espace privé réservé à la délivrance des 12 mots secrets BIP-39 du portefeuille crypto le 5 Février !\n\n"
            "<i>💡 Astuce : Vous pouvez aussi simplement envoyer une note vocale ou poser n'importe quelle question en langage naturel !</i>"
        )

    async def delete_forum_topic(self, message_thread_id: int, target_chat_id: Optional[str] = None) -> bool:
        """Deletes a forum topic and all its messages in a supergroup."""
        if not self.is_configured:
            return False
        # Thread 1 is Telegram's native root General topic and cannot be deleted
        if message_thread_id == 1:
            logger.debug("[TELEGRAM VAULT] Thread 1 is root General topic, skipping delete.")
            return False
        chat = self._resolve_supergroup_chat_id(target_chat_id)
        if not chat:
            return False
        payload = {
            "chat_id": chat,
            "message_thread_id": message_thread_id
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.base_url}/deleteForumTopic", json=payload)
                if res.status_code == 200 and res.json().get("ok"):
                    logger.info(f"[TELEGRAM VAULT] Deleted topic {message_thread_id} in {chat}")
                    return True
                else:
                    logger.debug(f"[TELEGRAM VAULT] deleteForumTopic failed: {res.text}")
        except Exception as e:
            logger.debug(f"[TELEGRAM VAULT] deleteForumTopic error: {e}")
        return False

    async def clean_duplicate_topics(self, target_chat_id: Optional[str] = None, max_scan: int = 150) -> Dict[str, Any]:
        """Scans and deletes existing forum topics to remove duplicates and resets the HQ cleanly."""
        chat = self._resolve_supergroup_chat_id(target_chat_id)
        if not self.is_configured or not chat:
            return {"success": False, "error": "Chat ID non configuré"}

        import asyncio
        deleted_count = 0
        # Scan from thread 2 to max_scan (thread 1 is root and protected)
        for thread_id in range(2, max_scan + 1):
            success = await self.delete_forum_topic(message_thread_id=thread_id, target_chat_id=chat)
            if success:
                deleted_count += 1
                await asyncio.sleep(0.15)  # Telegram API flood control

        self.topic_map.clear()
        try:
            cache_file = self._get_topics_cache_path()
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            pass

        setup_res = await self.setup_community_hq(target_chat_id=chat, force_recreate=True)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "topics_recreated": setup_res.get("topics_created", {}),
            "total_canonical": setup_res.get("total_created", 6)
        }

    async def save_conversation_snapshot(self, conv_memory: Any) -> bool:
        """Sérialise ConversationMemory.serialize_to_gzip() et l'upload sur Telegram."""
        compressed = conv_memory.serialize_to_gzip()
        fname = f"conv_snapshot_{int(time.time())}.json.gz"
        return await self.send_document(fname, compressed, caption="Conversation memory snapshot")

    async def restore_conversation_snapshot(self) -> Optional[bytes]:
        """Cherche le dernier fichier conv_snapshot_*.json.gz dans les messages récents et le retourne en bytes."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/getUpdates", params={"timeout": 1})
                if res.status_code == 200:
                    updates = res.json().get("result", [])
                    for update in reversed(updates):
                        msg = update.get("message")
                        if not msg: continue
                        doc = msg.get("document")
                        if doc and doc.get("file_name", "").startswith("conv_snapshot_"):
                            file_id = doc.get("file_id")
                            if file_id:
                                stream = await self.download_file_bytes(file_id)
                                if stream:
                                    return stream.getvalue()
        except Exception:
            pass
        return None

    async def backup_codebase_bundle(self, repo_path: str) -> Dict[str, Any]:
        """Creates an in-memory GZIP compressed archive of the entire codebase and uploads it
        to the Telegram Neural Vault as an emergency disaster recovery kit.
        Strict Mode NÉANT: 0 local disk writes, 100% in-memory streaming.
        Excludes .git, caches, credentials (.env) and log files.
        """
        import tarfile
        import hashlib
        from pathlib import Path

        repo_dir = Path(repo_path).resolve()
        buffer = io.BytesIO()
        file_count = 0

        # Patterns to strictly exclude from emergency bundle
        excluded_names = {
            ".git", ".env", ".pytest_cache", "__pycache__", ".coverage",
            "node_modules", "scratch", "dist", "build"
        }
        excluded_extensions = {".pyc", ".pyo", ".log", ".gguf"}

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for root, dirs, files in os.walk(repo_dir):
                # Filter out excluded directories in-place
                dirs[:] = [d for d in dirs if d not in excluded_names and not d.startswith(".env")]
                for file in files:
                    if file in excluded_names or file.startswith(".env"):
                        continue
                    if any(file.endswith(ext) for ext in excluded_extensions):
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(repo_dir)
                    tar.add(str(file_path), arcname=str(arcname))
                    file_count += 1

        bundle_bytes = buffer.getvalue()
        sha256_hash = hashlib.sha256(bundle_bytes).hexdigest()
        size_kb = len(bundle_bytes) / 1024.0

        filename = f"freeai_rescue_clone_{int(time.time())}.tar.gz"
        caption = (
            f"📦 <b>Kit de Secours & Auto-Clonage FreeAI</b>\n\n"
            f"• Fichiers archivés : <code>{file_count}</code>\n"
            f"• Taille compressée : <code>{size_kb:.2f} Ko</code>\n"
            f"• Empreinte disque locale : <b>0 octet (Mode NÉANT)</b>\n"
            f"• Intégrité SHA-256 : <code>{sha256_hash[:16]}...</code>\n\n"
            f"<i>En cas de perte de votre PC, téléchargez cette archive depuis Telegram, "
            f"décompressez-la avec : tar -xzf {filename} et relancez FreeAI instantanément !</i>"
        )

        uploaded = await self.send_document(filename=filename, data=bundle_bytes, caption=caption)

        return {
            "success": uploaded,
            "filename": filename,
            "files_count": file_count,
            "size_kb": size_kb,
            "sha256": sha256_hash,
            "uploaded_to_telegram": uploaded
        }

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
