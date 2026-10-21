"""Intégration réelle Starlink (dish locale sur 192.168.100.1:9200).

Si l'utilisateur possède une parabole Starlink, elle expose une API gRPC locale.
Ce module s'y connecte réellement quand c'est possible, et retourne un état
"non configuré" explicite sinon (jamais de donnée inventée).

Activation :
- pip install starlink-grpc-core (ou grpcio + le proto SpaceX officiel)
- Configurer STARLINK_IP dans .env (défaut : 192.168.100.1)
"""

import os
import socket
import logging
from typing import Optional

logger = logging.getLogger("starlink_adapter")

DEFAULT_STARLINK_IP = "192.168.100.1"
DEFAULT_STARLINK_PORT = 9200


class StarlinkAdapter:
    """Passerelle réelle vers le terminal utilisateur Starlink (gRPC local)."""

    def __init__(self, host: Optional[str] = None, port: int = DEFAULT_STARLINK_PORT, timeout_sec: float = 1.5):
        self.host = host or os.environ.get("STARLINK_IP", DEFAULT_STARLINK_IP)
        self.port = port
        self.timeout_sec = timeout_sec

    def is_dish_reachable(self) -> bool:
        """Sonde TCP réelle : True si un terminal Starlink répond sur host:port."""
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_sec):
                return True
        except OSError:
            return False

    def _get_grpc_status(self):
        """Récupère le statut réel via starlink_grpc si la librairie est installée."""
        try:
            import starlink_grpc
        except ImportError:
            logger.info("Librairie 'starlink_grpc' non installée : pip install starlink-grpc-core")
            return None

        try:
            return starlink_grpc.get_status(context=starlink_grpc.ChannelContext(target=f"{self.host}:{self.port}"))
        except Exception as e:
            logger.warning(f"Échec de la requête gRPC Starlink ({self.host}:{self.port}): {e}")
            return None

    async def get_signal_quality(self) -> Optional[float]:
        """Retourne la qualité de signal réelle (0-1) si un dish Starlink est joignable, None sinon."""
        if not self.is_dish_reachable():
            return None
        status = self._get_grpc_status()
        if status is None:
            return None
        # starlink_grpc expose pop_ping_drop_rate (0 = parfait, 1 = 100% de pertes)
        drop_rate = getattr(status, "pop_ping_drop_rate", None)
        if drop_rate is None:
            return None
        return max(0.0, min(1.0, 1.0 - float(drop_rate)))

    async def get_visible_satellites(self) -> int:
        """Nombre réel de satellites Starlink visibles (0 si dish absent ou non instrumenté)."""
        if not self.is_dish_reachable():
            return 0
        status = self._get_grpc_status()
        if status is None:
            return 0
        return int(getattr(status, "visible_satellites", 0) or 0)

    async def get_full_status(self) -> dict:
        """Diagnostic complet, utile pour /satellite starlink."""
        reachable = self.is_dish_reachable()
        return {
            "configured_host": self.host,
            "dish_reachable": reachable,
            "signal_quality": await self.get_signal_quality() if reachable else None,
            "visible_satellites": await self.get_visible_satellites() if reachable else 0,
        }
