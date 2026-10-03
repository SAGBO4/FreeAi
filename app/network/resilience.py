"""
NetworkResilience — Jarvis ne perd jamais internet.
Cascade de connexion : WiFi → Hotspot Android → GitHub Actions Cloud.
Mode NÉANT : 0 octet disque. Surveille, détecte, bascule, notifie.
"""

import asyncio
import httpx
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger("network_resilience")

class NetworkResilience:
    CONNECTIVITY_TARGETS = [
        "https://1.1.1.1",          # Cloudflare (ultra-fiable)
        "https://8.8.8.8",          # Google DNS
        "https://api.groq.com",     # FreeAI dépend de Groq
    ]
    
    def __init__(self, telegram_vault):
        self.telegram_vault = telegram_vault
        self.is_online = True
        self.last_latency_ms = 0.0
        self.active_interface = "wifi"
        self.cloud_mode_active = False
        self.uptime_percentage = 100.0
        self.disconnection_count = 0
        self._adb_available = self._check_command("adb")
        self._nmcli_available = self._check_command("nmcli")
        self._total_checks = 0
        self._online_checks = 0

    def _check_command(self, cmd: str) -> bool:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    async def check_connectivity(self) -> Dict[str, Any]:
        """Ping multiple cibles, retourne latence moyenne et statut."""
        async def ping(target: str) -> Optional[float]:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    start = asyncio.get_event_loop().time()
                    resp = await client.get(target)
                    resp.raise_for_status()
                    return (asyncio.get_event_loop().time() - start) * 1000
            except Exception:
                return None

        results = await asyncio.gather(*(ping(t) for t in self.CONNECTIVITY_TARGETS))
        latencies = [l for l in results if l is not None]
        
        self._total_checks += 1
        
        if latencies:
            self._online_checks += 1
            self.last_latency_ms = sum(latencies) / len(latencies)
            status = {"online": True, "latency_ms": self.last_latency_ms, "provider": "multiple"}
        else:
            self.last_latency_ms = 0.0
            status = {"online": False, "latency_ms": 0.0, "provider": "none"}
            
        self.uptime_percentage = (self._online_checks / self._total_checks) * 100.0
        return status

    async def monitor_loop(self, interval_sec: int = 10):
        """Boucle asyncio infinie : check toutes les N secondes.
        Si online → status OK.
        Si offline → déclenche cascade_fallback().
        Si revient → notifie Telegram + resync.
        """
        logger.info("[JARVIS NETWORK] Démarrage du monitor_loop (Mode NÉANT)")
        while True:
            try:
                status = await self.check_connectivity()
                
                if status["online"]:
                    if not self.is_online or self.cloud_mode_active:
                        await self.on_connectivity_restored()
                    self.is_online = True
                else:
                    if self.is_online:
                        self.disconnection_count += 1
                        logger.warning("[JARVIS NETWORK] Perte de connexion détectée ! Basculement...")
                        self.is_online = False
                        self.active_interface = await self.cascade_fallback()
                        
                await asyncio.sleep(interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[JARVIS NETWORK] Erreur monitor_loop: {e}")
                await asyncio.sleep(interval_sec)

    async def cascade_fallback(self) -> str:
        """
        Ordre de tentative :
        1. WiFi autre réseau (scan via nmcli si disponible)
        2. Hotspot Android via ADB (si câble USB connecté)
        3. Mode cloud : notifie que GitHub Actions prend le relais
        Retourne la source active ou 'cloud_only'
        """
        logger.info("[JARVIS NETWORK] Cascade de fallback initiée")
        
        if self._nmcli_available:
            logger.info("[JARVIS NETWORK] Tentative WiFi Failover...")
            if await self.try_wifi_failover():
                return "wifi"
                
        if self._adb_available:
            logger.info("[JARVIS NETWORK] Tentative Hotspot Android (ADB)...")
            if await self.try_android_hotspot():
                return "hotspot"
                
        logger.warning("[JARVIS NETWORK] Toutes les tentatives locales ont échoué.")
        await self.trigger_cloud_mode()
        return "cloud_only"

    async def try_android_hotspot(self) -> bool:
        """
        Tente d'activer le hotspot Android via ADB USB.
        """
        if not self._adb_available:
            return False
            
        try:
            # Check devices
            proc = await asyncio.create_subprocess_exec(
                "adb", "devices", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if b"device\n" not in stdout and b"device\r\n" not in stdout:
                logger.warning("[JARVIS NETWORK] Aucun appareil Android connecté via ADB.")
                return False
                
            # Enable hotspot
            cmd = "adb shell svc wifi enable && adb shell cmd connectivity start-wifi"
            proc = await asyncio.create_subprocess_shell(cmd)
            await asyncio.wait_for(proc.communicate(), timeout=8.0)
            
            # Wait and check
            await asyncio.sleep(5)
            status = await self.check_connectivity()
            return status["online"]
        except Exception as e:
            logger.error(f"[JARVIS NETWORK] Erreur try_android_hotspot: {e}")
            return False

    async def try_wifi_failover(self) -> bool:
        """
        Via nmcli (Linux), liste les réseaux WiFi disponibles et tente
        de se connecter au premier réseau connu.
        """
        if not self._nmcli_available:
            return False
            
        try:
            proc = await asyncio.create_subprocess_exec(
                "nmcli", "-t", "-f", "NAME", "connection", "show",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            known_networks = [n for n in stdout.decode().strip().split('\n') if n]
            
            if not known_networks:
                return False
                
            # Just try the first known network that is not the current one
            # In a real scenario, we'd check current, but for fallback we just try 'up'
            target = known_networks[0]
            proc = await asyncio.create_subprocess_exec(
                "nmcli", "connection", "up", target,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=10.0)
            
            status = await self.check_connectivity()
            return status["online"]
        except Exception as e:
            logger.error(f"[JARVIS NETWORK] Erreur try_wifi_failover: {e}")
            return False

    async def trigger_cloud_mode(self) -> bool:
        """
        Quand AUCUNE connexion locale n'est disponible.
        """
        self.cloud_mode_active = True
        logger.warning("[JARVIS NETWORK] Mode cloud forcé activé (GitHub Actions prend le relais).")
        
        if self._adb_available:
            try:
                # Try to send a message via adb shell curl using phone's 4G
                msg = "⚠️ Jarvis hors ligne localement. Mode Cloud activé."
                cmd = f"adb shell 'curl -s -X POST https://api.telegram.org/bot<TOKEN>/sendMessage -d chat_id=<ID> -d text=\"{msg}\"'"
                proc = await asyncio.create_subprocess_shell(cmd)
                await asyncio.wait_for(proc.communicate(), timeout=10.0)
            except Exception:
                pass
                
        return True

    async def on_connectivity_restored(self):
        """Quand internet revient."""
        self.cloud_mode_active = False
        self.active_interface = "wifi"
        logger.info("[JARVIS NETWORK] 📡 Connexion restaurée ! Resync en cours...")
        try:
            await self.telegram_vault.send_message("📡 Connexion restaurée ! Resync en cours...")
        except Exception:
            pass

    def get_status(self) -> Dict:
        return {
            "online": self.is_online,
            "latency_ms": self.last_latency_ms,
            "active_interface": self.active_interface,
            "cloud_mode": self.cloud_mode_active,
            "uptime_pct": self.uptime_percentage,
            "disconnections_count": self.disconnection_count,
            "adb_available": self._adb_available,
        }
