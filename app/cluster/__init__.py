"""Cluster & Distributed Compute Swarm Package for FreeAI."""

from app.cluster.swarm import LANClusterManager, ComputeNode
from app.cluster.autonomous_members import (
    MemberPrivilege,
    MemberSpecialty,
    MissionStatus,
    AutonomousMission,
    AutonomousMemberBot,
    FreeAiMemberRegistry,
    AutonomousMemberSwarm
)

__all__ = [
    "LANClusterManager",
    "ComputeNode",
    "MemberPrivilege",
    "MemberSpecialty",
    "MissionStatus",
    "AutonomousMission",
    "AutonomousMemberBot",
    "FreeAiMemberRegistry",
    "AutonomousMemberSwarm"
]
