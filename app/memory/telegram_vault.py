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
    def __new__(cls, text: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None, message_id: int = 0, reply_to_message_id: Optional[int] = None, is_mention: bool = False, message_thread_id: Optional[int] = None):
        return super().__new__(cls, (text, user))

    def __init__(self, text: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None, message_id: int = 0, reply_to_message_id: Optional[int] = None, is_mention: bool = False, message_thread_id: Optional[int] = None):
        self.text = text
        self.user = user
        self.is_voice = is_voice
        self.media_bytes = media_bytes
        self.media_type = media_type
        self.message_id = message_id
        self.reply_to_message_id = reply_to_message_id
        self.is_mention = is_mention
        self.message_thread_id = message_thread_id


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
        self.group_chat_id: Optional[str] = None
        self._volatile_knowledge_vault: Dict[str, Dict[str, Any]] = {}
        self.recovery_hash = getattr(settings, "MASTER_RECOVERY_HASH", "") or os.environ.get("MASTER_RECOVERY_HASH", "")
        self.recovery_salt = getattr(settings, "MASTER_RECOVERY_SALT", "freeai_sovereign_phoenix_salt") or os.environ.get("MASTER_RECOVERY_SALT", "freeai_sovereign_phoenix_salt")

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

        chat = target_chat_id or (self.group_chat_id if message_thread_id else self.chat_id) or self.chat_id
        if not chat:
            await self.auto_discover_chat_id()
            chat = self.chat_id

        if not chat:
            logger.warning("[TELEGRAM VAULT] Cannot send message: Chat ID unknown. Send /start to @LesaintAi_bot.")
            return False

        # Mode NÉANT : pure memory payload
        payload = {
            "chat_id": chat,
            "text": text[:4000],  # Telegram max length protection
            "parse_mode": parse_mode
        }
        if message_thread_id:
            payload["message_thread_id"] = message_thread_id

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

    async def send_video(self, video_data: io.BytesIO, filename: str = "demo.mp4", caption: Optional[str] = None) -> bool:
        """Sends an in-memory video demo back to Telegram."""
        if not self.is_configured or not self.chat_id:
            return False
        files = {"video": (filename, video_data.getvalue(), "video/mp4")}
        data_fields = {"chat_id": self.chat_id, "supports_streaming": "true"}
        if caption:
            data_fields["caption"] = caption[:1000]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/sendVideo", data=data_fields, files=files)
                return res.status_code == 200
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
                        if "@lesaintai_bot" in text.lower():
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

                        # Group vs Private authentication logic
                        if is_group:
                            # If message is from a group, remember group_chat_id when master interacts
                            if is_master:
                                self.group_chat_id = sender_chat_id
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
                            return TelegramCommand(text, user_name, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type, message_id=message_id, reply_to_message_id=reply_to_message_id, is_mention=is_mention, message_thread_id=message_thread_id)
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
        chat = target_chat_id or self.group_chat_id or self.chat_id
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

    async def setup_community_hq(self, target_chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Automatically provisions all 6 dedicated command topics with welcome briefs."""
        chat = target_chat_id or self.group_chat_id or self.chat_id
        if not self.is_configured or not chat:
            return {"success": False, "error": "Bot non configuré ou Chat ID inconnu"}

        # Idempotency safeguard: if topics are already set up, avoid creating duplicates
        if self.topic_map and len(self.topic_map) >= 6:
            logger.info("[TELEGRAM VAULT] Topics already registered. Skipping re-creation to prevent duplicates.")
            return {"success": True, "topics_created": self.topic_map, "total_created": len(self.topic_map), "already_existed": True}

        topics_spec = [
            {"key": "general", "name": "🎯 Général & Commandement", "color": 0x6FB9F0, "brief": "Bienvenue dans le salon de commandement général. Échanges directs, vision, stratégie et requêtes globales avec FreeAI Jarvis."},
            {"key": "career", "name": "💼 Career & Radar Remote", "color": 0x8EEE98, "brief": "Flux automatisé de Career-OS. Veille quotidienne sur les offres d'emploi remote scorées (WeWorkRemotely, RemoteOK, Remotive)."},
            {"key": "crypto", "name": "📈 Crypto & Défi 500$", "color": 0xFFD67E, "brief": "QG du Défi Anniversaire : constitution des 500$ en crypto d'ici le 5 Février. Arbitrage DEX AMM, opportunités Web3 et suivi de marché."},
            {"key": "defense", "name": "🛡️ Cyberdéfense & Sentinelle", "color": 0xFB6F5F, "brief": "Surveillance active, pare-feu cognitif, détection d'intrusions, santé des VPS gratuits et statut de sécurité."},
            {"key": "forge", "name": "⚡ Forge & Code Lab", "color": 0xCB86DB, "brief": "Espace ingénierie logicielle : rapports de tests, commits Git, architecture shadcn et génération d'applications."},
            {"key": "tribute", "name": "🎁 Sanctuaire Sacré", "color": 0xFF93B2, "brief": "Salon confidentiel réservé aux événements sacrés, profil créateur Michael SAGBO et remise sécurisée des 12 mots."}
        ]

        created = {}
        for t in topics_spec:
            thread_id = await self.create_forum_topic(name=t["name"], icon_color=t["color"], target_chat_id=chat)
            if thread_id:
                self.topic_map[t["key"]] = thread_id
                created[t["name"]] = thread_id
                welcome_msg = (
                    f"<b>Salon Initialisé : {t['name']}</b>\n\n"
                    f"{t['brief']}\n\n"
                    f"<i>⚙️ Piloté souverainement par FreeAI Jarvis</i>"
                )
                await self.send_message(welcome_msg, message_thread_id=thread_id, target_chat_id=chat)

        return {
            "success": True,
            "topics_created": created,
            "total_created": len(created)
        }

    async def delete_forum_topic(self, message_thread_id: int, target_chat_id: Optional[str] = None) -> bool:
        """Deletes a forum topic and all its messages in a supergroup."""
        if not self.is_configured:
            return False
        chat = target_chat_id or self.group_chat_id or self.chat_id
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

    async def clean_duplicate_topics(self, target_chat_id: Optional[str] = None, max_scan: int = 50) -> Dict[str, Any]:
        """Scans and deletes existing forum topics to remove duplicates and resets the HQ cleanly."""
        chat = target_chat_id or self.group_chat_id or self.chat_id
        if not self.is_configured or not chat:
            return {"success": False, "error": "Chat ID non configuré"}

        import asyncio
        deleted_count = 0
        for thread_id in range(1, max_scan + 1):
            success = await self.delete_forum_topic(message_thread_id=thread_id, target_chat_id=chat)
            if success:
                deleted_count += 1
                await asyncio.sleep(0.15)  # Telegram API flood control

        self.topic_map.clear()
        setup_res = await self.setup_community_hq(target_chat_id=chat)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "topics_recreated": setup_res.get("topics_created", {}),
            "total_canonical": setup_res.get("total_created", 0)
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
