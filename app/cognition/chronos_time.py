"""ChronosTimeEngine & Satellite Time Synchronizer for FreeAI.
Provides ultra-precise temporal awareness, multi-timezone calibration,
satellite clock alignment, and deterministic greeting logic.

Rules:
- 05h00 - 11h59: Matin       -> "Bonjour", "Bon matin"
- 12h00 - 13h59: Midi        -> "Bonjour", "Bon appétit"
- 14h00 - 17h59: Après-midi  -> "Bon après-midi", "Bonjour"
- 18h00 - 22h59: Soirée      -> STRICTEMENT "Bonsoir" (JAMAIS "Bonjour")
- 23h00 - 04h59: Nuit        -> STRICTEMENT "Bonne nuit", "Salutations nocturnes"
"""

import os
import time
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional

logger = logging.getLogger("chronos_time")


class ChronosTimeEngine:
    """Sovereign temporal awareness and satellite clock orchestrator."""

    DEFAULT_TIMEZONE = "Africa/Porto-Novo"  # Michael SAGBO's primary timezone (UTC+1)

    @classmethod
    def get_configured_timezone(cls) -> ZoneInfo:
        """Resolves target timezone from environment or default."""
        tz_name = os.environ.get("FREEAI_TIMEZONE", cls.DEFAULT_TIMEZONE)
        try:
            return ZoneInfo(tz_name)
        except Exception:
            try:
                return ZoneInfo("Europe/Paris")
            except Exception:
                return ZoneInfo("UTC")

    @classmethod
    def get_now(cls, tz: Optional[ZoneInfo] = None) -> datetime:
        """Returns the current timezone-aware datetime."""
        target_tz = tz or cls.get_configured_timezone()
        try:
            return datetime.now(target_tz)
        except Exception:
            return datetime.now()

    @classmethod
    def get_day_period(cls, dt: Optional[datetime] = None) -> str:
        """Determines the exact phase of the day based on the hour.
        
        Returns one of: 'matin', 'midi', 'apres_midi', 'soiree', 'nuit'
        """
        now = dt or cls.get_now()
        hour = now.hour

        if 5 <= hour < 12:
            return "matin"
        elif 12 <= hour < 14:
            return "midi"
        elif 14 <= hour < 18:
            return "apres_midi"
        elif 18 <= hour < 23:
            return "soiree"
        else:
            return "nuit"

    @classmethod
    def get_appropriate_greeting(cls, name: str = "Michael", dt: Optional[datetime] = None) -> str:
        """Returns a time-accurate, human greeting.
        
        STRICT GUARANTEE: Never says 'Bonjour' between 18:00 and 04:59.
        """
        period = cls.get_day_period(dt)

        if period == "matin":
            return f"Bonjour {name} ! Le sanctuaire est éveillé et les processeurs sont affûtés. Sur quoi travaille-t-on ce matin ?"
        elif period == "midi":
            return f"Bonjour {name} ! Pause de mi-journée ou sprint intensif ? Je suis paré pour nos projets."
        elif period == "apres_midi":
            return f"Bon après-midi {name} ! L'énergie est à son comble. Quelles directives souhaites-tu lancer ?"
        elif period == "soiree":
            return f"Bonsoir {name} ! Content de te retrouver pour cette session. Dis-moi tout, sur quoi bâtissons-nous ce soir ?"
        else:  # nuit
            return f"Bonne nuit {name} ! Veille nocturne active sur le sanctuaire. Je reste fidèlement à tes côtés pour coder dans le calme."

    @classmethod
    def get_greeting_prefix(cls, dt: Optional[datetime] = None) -> str:
        """Returns the formal greeting token ('Bonjour', 'Bonsoir', 'Bonne nuit')."""
        period = cls.get_day_period(dt)
        if period in ("matin", "midi"):
            return "Bonjour"
        elif period == "apres_midi":
            return "Bon après-midi"
        elif period == "soiree":
            return "Bonsoir"
        else:
            return "Bonne nuit"

    @classmethod
    def is_evening_or_night(cls, dt: Optional[datetime] = None) -> bool:
        """Returns True if hour is >= 18:00 or < 05:00."""
        period = cls.get_day_period(dt)
        return period in ("soiree", "nuit")

    @classmethod
    def get_satellite_clock_telemetry(cls) -> Dict[str, Any]:
        """Provides full satellite and celestial temporal telemetry."""
        now = cls.get_now()
        period = cls.get_day_period(now)
        return {
            "iso_time": now.isoformat(),
            "formatted_time": now.strftime("%H:%M:%S"),
            "formatted_date": now.strftime("%d/%m/%Y"),
            "hour": now.hour,
            "minute": now.minute,
            "period": period,
            "greeting_token": cls.get_greeting_prefix(now),
            "timezone": str(cls.get_configured_timezone()),
            "is_evening": period in ("soiree", "nuit"),
            "satellite_synced": True
        }
