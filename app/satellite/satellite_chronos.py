"""SatelliteChronos — Horloge Satellitaire & Conscience Temporelle Déterministe.
Couplage de l'heure système avec la géolocalisation et données satellitaires (SatelliteEye).
Classification déterministe et subtile des phases du jour (aube, matin, midi, après-midi,
crépuscule/soirée dès 18h, nuit).
Élimine définitivement les incohérences de salutation ('bonjour' à 18h) dans FreeAI Jarvis.
Mode NÉANT : 100% en mémoire, zéro latence.
"""

import time
import math
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("satellite_chronos")


class DayPhase(str, Enum):
    AUBE = "aube"               # 05h00 - 06h59 (Lueurs de l'aube)
    MATIN = "matin"             # 07h00 - 11h59 (Plein matin)
    MIDI = "midi"               # 12h00 - 13h59 (Zénith & pause méridienne)
    APRES_MIDI = "apres_midi"   # 14h00 - 17h59 (Après-midi studieuse)
    SOIREE = "soiree"           # 18h00 - 22h59 (Crépuscule & soirée — STRICTEMENT BONSOIR)
    NUIT = "nuit"               # 23h00 - 04h59 (Nuit profonde & veille nocturne)


class SatelliteChronos:
    """Moteur de Conscience Temporelle Satellitaire pour FreeAI Jarvis."""

    DEFAULT_LAT = 48.8566  # Paris / Zone Europe de l'Ouest par défaut
    DEFAULT_LON = 2.3522

    def __init__(self, lat: Optional[float] = None, lon: Optional[float] = None, tz_offset_hours: Optional[float] = None):
        self.lat = lat if lat is not None else self.DEFAULT_LAT
        self.lon = lon if lon is not None else self.DEFAULT_LON
        self.tz_offset_hours = tz_offset_hours
        self._last_satellite_sync = 0.0

    def set_coordinates(self, lat: float, lon: float) -> None:
        """Met à jour les coordonnées géographiques issues du radar satellitaire."""
        self.lat = lat
        self.lon = lon
        self._last_satellite_sync = time.time()

    def get_local_datetime(self) -> datetime:
        """Retourne la date et l'heure locale déterminée."""
        if self.tz_offset_hours is not None:
            tz = timezone(timedelta(hours=self.tz_offset_hours))
            return datetime.now(tz)
        # Heure locale système de la machine de Michael
        return datetime.now()

    def classify_phase(self, dt: Optional[datetime] = None) -> DayPhase:
        """Détermine la phase exacte de la journée avec frontière stricte à 18h00."""
        target_dt = dt or self.get_local_datetime()
        hour = target_dt.hour
        minute = target_dt.minute
        time_decimal = hour + (minute / 60.0)

        if 5.0 <= time_decimal < 7.0:
            return DayPhase.AUBE
        elif 7.0 <= time_decimal < 12.0:
            return DayPhase.MATIN
        elif 12.0 <= time_decimal < 14.0:
            return DayPhase.MIDI
        elif 14.0 <= time_decimal < 18.0:
            return DayPhase.APRES_MIDI
        elif 18.0 <= time_decimal < 23.0:
            # Dès 18h00 pile, bascule immédiate et irrévocable en soirée !
            return DayPhase.SOIREE
        else:
            return DayPhase.NUIT

    def get_salutation(self, dt: Optional[datetime] = None) -> str:
        """Retourne la salutation polie rigoureuse adaptée à la phase courante."""
        phase = self.classify_phase(dt)
        if phase in (DayPhase.SOIREE, DayPhase.NUIT):
            return "Bonsoir"
        return "Bonjour"

    def get_greeting_sentence(self, user_name: str = "Michael", dt: Optional[datetime] = None) -> str:
        """Génère une formule d'accueil naturelle, dynamique et impeccable."""
        phase = self.classify_phase(dt)
        target_dt = dt or self.get_local_datetime()
        hour_str = target_dt.strftime("%H:%M")

        if phase == DayPhase.AUBE:
            return f"Bonjour {user_name} ! Aux premières lueurs du jour ({hour_str}), FreeAI est éveillé et prêt."
        elif phase == DayPhase.MATIN:
            return f"Bonjour {user_name} ! J'espère que ta matinée commence sous les meilleurs auspices."
        elif phase == DayPhase.MIDI:
            return f"Bonjour {user_name} ! Il est {hour_str}, pause méridienne ou session intensive en cours ?"
        elif phase == DayPhase.APRES_MIDI:
            return f"Bonjour {user_name} ! En plein cœur de l'après-midi, tous nos moteurs sont parés."
        elif phase == DayPhase.SOIREE:
            # RÈGLE ABSOLUE : Bonsoir dès 18h
            return f"Bonsoir {user_name} ! Le crépuscule s'installe ({hour_str}), je suis à ton écoute."
        else:  # NUIT
            return f"Bonsoir {user_name} ! En pleine session nocturne ({hour_str}), le sanctuaire veille sur tes projets."

    def get_temporal_context_for_llm(self, dt: Optional[datetime] = None) -> str:
        """Fournit les instructions temporelles déterministes à injecter dans le prompt système du LLM."""
        target_dt = dt or self.get_local_datetime()
        phase = self.classify_phase(target_dt)
        salutation = self.get_salutation(target_dt)
        hour_str = target_dt.strftime("%H:%M")
        date_str = target_dt.strftime("%d/%m/%Y")

        phase_descriptions = {
            DayPhase.AUBE: "l'aube (premières lueurs du jour)",
            DayPhase.MATIN: "le matin (session matinale)",
            DayPhase.MIDI: "le midi (milieu de journée)",
            DayPhase.APRES_MIDI: "l'après-midi",
            DayPhase.SOIREE: "la soirée (crépuscule et début de nuit)",
            DayPhase.NUIT: "la nuit (session nocturne tardive)",
        }

        context = (
            f"HORLOGE SATELLITAIRE & CONSCIENCE TEMPORELLE (Contexte temporel) :\n"
            f"- Date actuelle : {date_str} | Heure exacte : {hour_str}\n"
            f"- Phase du jour : {phase.value.upper()} ({phase_descriptions[phase]})\n"
            f"- SALUTATION REQUISE : '{salutation}' (RÈGLE STRICTE : Ne dis JAMAIS 'Bonjour' si phase=SOIREE ou NUIT, utilise EXCLUSIVEMENT '{salutation}').\n"
            f"- Ton et ambiance : adapte ton énergie temporelle à cette tranche horaire."
        )
        return context

    def get_solar_ephemeris(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        """Calcul frugal de la déclinaison solaire et de la hauteur approchée du soleil en RAM."""
        target_dt = dt or self.get_local_datetime()
        day_of_year = target_dt.timetuple().tm_yday
        hour = target_dt.hour + target_dt.minute / 60.0

        # Approximation équation du temps & déclinaison solaire
        declination = 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))
        lat_rad = math.radians(self.lat)
        dec_rad = math.radians(declination)
        hour_angle = math.radians(15.0 * (hour - 12.0))

        elevation = math.degrees(
            math.asin(
                math.sin(lat_rad) * math.sin(dec_rad)
                + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_angle)
            )
        )

        is_sun_up = elevation > 0.0

        return {
            "solar_elevation_deg": round(elevation, 2),
            "is_daylight": is_sun_up,
            "declination_deg": round(declination, 2),
            "hour_decimal": round(hour, 2),
            "phase": self.classify_phase(target_dt).value
        }
