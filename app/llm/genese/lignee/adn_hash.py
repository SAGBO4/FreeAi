import hashlib
import json
import dataclasses
from ..evolution.genome import Genome

def hacher_lignee(hash_parent: str, genome: Genome, scores: dict) -> str:
    """
    Génère un hash SHA-256 chaîné pour valider la lignée évolutive de Jarvis.
    hash = SHA-256(hash_parent + genome_json + scores_json)
    """
    data = {
        "parent": hash_parent,
        "genome": dataclasses.asdict(genome) if hasattr(genome, '__dataclass_fields__') else {},
        "scores": scores
    }
    encoded = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
