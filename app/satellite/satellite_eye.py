"""
SatelliteEye — L'Œil de Dieu de FreeAI Jarvis.
Surveillance satellite globale, omnipresente, temps réel.
DISPONIBLE UNIQUEMENT EN MODE lesaintAi (sudo root).
Mode NÉANT : 0 octet sur disque, 100% RAM.
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional, Tuple

class SatelliteEye:
    def __init__(self, mode: str):
        self._check_sudo_mode(mode)
        self.timeout = 10.0
        self.headers = {'User-Agent': 'FreeAI-Jarvis-SatelliteEye/1.0'}

    def _check_sudo_mode(self, mode: str) -> None:
        """Vérifie que le mode lesaintAi est actif — sinon refuse."""
        if mode != "lesaintAi":
            raise PermissionError(
                "🔒 SatelliteEye est réservé au mode lesaintAi God-Mode. "
                "Activez le mode souverain pour accéder à l'Œil de Dieu."
            )

    async def geocode(self, location_name: str) -> Optional[Tuple[float, float]]:
        url = f"https://nominatim.openstreetmap.org/search?q={location_name}&format=json&limit=1"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            pass
        return None

    async def get_aircraft_overhead(self, lat: float, lon: float, radius_deg: float = 3.0) -> List[Dict]:
        url = f"https://opensky-network.org/api/states/all?lamin={lat-radius_deg}&lomin={lon-radius_deg}&lamax={lat+radius_deg}&lomax={lon+radius_deg}"
        aircraft_list = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                states = data.get("states")
                if states:
                    for s in states[:15]: # Limit to 15 to avoid massive output
                        aircraft_list.append({
                            "callsign": s[1].strip() if s[1] else "UNKNOWN",
                            "origin_country": s[2],
                            "longitude": s[5],
                            "latitude": s[6],
                            "altitude": s[7], # baro_altitude
                            "velocity": s[9] # m/s
                        })
        except Exception:
            pass
        return aircraft_list

    async def get_natural_events(self) -> List[Dict]:
        url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=20"
        events_list = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                events = data.get("events", [])
                for e in events:
                    events_list.append({
                        "id": e.get("id"),
                        "title": e.get("title"),
                        "categories": [c["title"] for c in e.get("categories", [])],
                        "geometry": e.get("geometry", [{}])[0]
                    })
        except Exception:
            pass
        return events_list

    async def get_iss_position(self) -> Dict:
        url = "https://api.wheretheiss.at/v1/satellites/25544"
        iss_data = {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                iss_data = {
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "altitude": data.get("altitude"),
                    "velocity": data.get("velocity")
                }
        except Exception:
            pass
        return iss_data

    async def get_satellite_weather(self, lat: float, lon: float) -> Dict:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,precipitation,cloud_cover,weather_code&wind_speed_unit=kmh"
        weather_data = {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()
                current = data.get("current", {})
                weather_data = {
                    "temperature_2m": current.get("temperature_2m"),
                    "cloud_cover": current.get("cloud_cover"),
                    "wind_speed_10m": current.get("wind_speed_10m"),
                    "precipitation": current.get("precipitation")
                }
        except Exception:
            pass
        return weather_data

    async def scan_zone(self, location: str) -> Dict[str, Any]:
        """
        Scan complet d'une zone : géolocalise, puis lance toutes les sources en parallèle.
        Retourne un rapport complet formaté pour Telegram.
        """
        coords = await self.geocode(location)
        if not coords:
            return {"error": f"Zone '{location}' introuvable", "formatted": f"❌ Zone '{location}' introuvable."}
        lat, lon = coords
        
        aircraft, events, iss, weather = await asyncio.gather(
            self.get_aircraft_overhead(lat, lon),
            self.get_natural_events(),
            self.get_iss_position(),
            self.get_satellite_weather(lat, lon),
            return_exceptions=True
        )
        
        # Clean exceptions if any
        aircraft = aircraft if not isinstance(aircraft, Exception) else []
        events = events if not isinstance(events, Exception) else []
        iss = iss if not isinstance(iss, Exception) else {}
        weather = weather if not isinstance(weather, Exception) else {}
        
        return self._format_satellite_report(location, lat, lon, aircraft, events, iss, weather)

    def _format_satellite_report(
        self, location: str, lat: float, lon: float, 
        aircraft: List[Dict], events: List[Dict], 
        iss: Dict, weather: Dict
    ) -> Dict:
        """Formate en HTML Telegram avec émojis et sections claires."""
        
        html = f"🛰️ <b>[SATELLITE EYE — {location}]</b>\n📍 {lat:.4f}°, {lon:.4f}°\n\n"
        
        # Aviation
        html += "✈️ <b>Aviation (Zone globale)</b>\n"
        if aircraft:
            for a in aircraft[:5]:
                alt = f"{a['altitude']}m" if a['altitude'] else "N/A"
                spd = f"{a['velocity']*3.6:.0f}km/h" if a['velocity'] else "N/A"
                html += f"• {a['callsign']} — {a['origin_country']} — {alt} — {spd}\n"
        else:
            html += "• Aucun aéronef détecté\n"
        
        html += "\n🌪️ <b>Alertes EONET actives</b>\n"
        if events:
            for e in events[:3]:
                html += f"• {e['title']} ({', '.join(e['categories'])})\n"
        else:
            html += "• Aucune menace naturelle globale active ou API indisponible ✅\n"
            
        html += "\n🌍 <b>ISS en ce moment</b>\n"
        if iss:
            html += f"• Position : {iss.get('latitude', 0):.2f}°, {iss.get('longitude', 0):.2f}°\n"
            html += f"• Altitude : {iss.get('altitude', 0):.0f} km • Vitesse : {iss.get('velocity', 0):.0f} km/h\n"
        else:
            html += "• Données ISS indisponibles\n"
            
        html += "\n🌤️ <b>Météo satellite</b>\n"
        if weather:
            html += f"• {weather.get('temperature_2m')}°C • Nuages : {weather.get('cloud_cover')}% • Vent : {weather.get('wind_speed_10m')} km/h\n"
            html += f"• Précipitations : {weather.get('precipitation')} mm\n"
        else:
            html += "• Données météo indisponibles\n"
            
        html += "\n<i>🔒 God-Mode lesaintAi — Jarvis voit tout.</i>"
        
        return {
            "location": location,
            "lat": lat,
            "lon": lon,
            "formatted": html,
            "raw": {
                "aircraft": aircraft,
                "events": events,
                "iss": iss,
                "weather": weather
            }
        }
