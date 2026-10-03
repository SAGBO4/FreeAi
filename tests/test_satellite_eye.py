import pytest
import asyncio
from typing import Dict, Any

from app.satellite.satellite_eye import SatelliteEye

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP Error")

class MockAsyncClient:
    def __init__(self, *args, **kwargs):
        pass
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def get(self, url, headers=None):
        if "nominatim" in url:
            if "Cotonou" in url:
                return MockResponse([{"lat": "6.3703", "lon": "2.3912"}])
            return MockResponse([])
        elif "opensky" in url:
            return MockResponse({
                "states": [
                    ["", "ABC123", "France", None, None, 2.3, 6.3, 11000, False, 236.1],
                    ["", "XYZ456", "Ethiopia", None, None, 2.4, 6.4, 9800, False, 216.6]
                ]
            })
        elif "eonet" in url:
            return MockResponse({"events": []})
        elif "wheretheiss" in url:
            return MockResponse({
                "latitude": 15.2,
                "longitude": 45.8,
                "altitude": 408.5,
                "velocity": 27600
            })
        elif "open-meteo" in url:
            return MockResponse({
                "current": {
                    "temperature_2m": 28.5,
                    "cloud_cover": 23,
                    "wind_speed_10m": 18.2,
                    "precipitation": 0.0
                }
            })
        return MockResponse({})


@pytest.fixture
def mock_httpx(monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)


def test_geocode_cotonou(mock_httpx):
    eye = SatelliteEye("lesaintAi")
    coords = asyncio.run(eye.geocode("Cotonou"))
    assert coords == (6.3703, 2.3912)


def test_aircraft_overhead(mock_httpx):
    eye = SatelliteEye("lesaintAi")
    aircraft = asyncio.run(eye.get_aircraft_overhead(6.3703, 2.3912))
    assert len(aircraft) == 2
    assert aircraft[0]["callsign"] == "ABC123"
    assert aircraft[0]["origin_country"] == "France"
    assert aircraft[0]["altitude"] == 11000


def test_natural_events_empty(mock_httpx):
    eye = SatelliteEye("lesaintAi")
    events = asyncio.run(eye.get_natural_events())
    assert len(events) == 0


def test_iss_position(mock_httpx):
    eye = SatelliteEye("lesaintAi")
    iss = asyncio.run(eye.get_iss_position())
    assert iss["altitude"] == 408.5
    assert iss["velocity"] == 27600


def test_scan_zone_parallel(mock_httpx):
    eye = SatelliteEye("lesaintAi")
    report = asyncio.run(eye.scan_zone("Cotonou"))
    
    assert report["lat"] == 6.3703
    assert report["lon"] == 2.3912
    assert "ABC123" in report["formatted"]
    assert "408 km" in report["formatted"]
    assert "28.5°C" in report["formatted"]
    assert "God-Mode lesaintAi" in report["formatted"]


def test_mode_guard():
    with pytest.raises(PermissionError, match="SatelliteEye est réservé au mode lesaintAi"):
        SatelliteEye("freeAi")

