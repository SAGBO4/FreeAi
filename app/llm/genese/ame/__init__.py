"""
Module Âme - Gardien Ethique pour Jarvis
"""

from .constitution import PRINCIPES
from .gardien import GardienEthique

try:
    from .ancrage import ElasticWeightConsolidation
    __all__ = ["PRINCIPES", "GardienEthique", "ElasticWeightConsolidation"]
except ImportError:
    __all__ = ["PRINCIPES", "GardienEthique"]
