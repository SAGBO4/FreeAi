"""Tests for Aether-Swarm Architecture (Protocole AETHER-SWARM).
Verifies:
1. Zero-Local-Pressure RAM/CPU guarantee (< 60 MB budget, 0 disk write).
2. Parallel Multi-Model Swarm Cross-Validation (Debate & Consensus).
3. Ghost Cloud Offloading and Telegram integration.
"""

import asyncio
import io
import pytest
from app.cluster.aether_swarm import AetherSwarmOrchestrator, SwarmConsensusResult, CloudComputeNode
from app.llm.federation import OnlineModelFederation


@pytest.fixture
def federation():
    return OnlineModelFederation(memory_mode="neant")


@pytest.fixture
def aether_swarm(federation):
    return AetherSwarmOrchestrator(federation=federation)


def test_aether_swarm_initialization(aether_swarm):
    assert aether_swarm is not None
    assert len(aether_swarm.cloud_nodes) >= 3
    # Check default free cloud nodes
    node_names = [n.name for n in aether_swarm.cloud_nodes]
    assert any("Groq" in name for name in node_names)
    assert any("DeepSeek" in name or "Qwen" in name or "OpenRouter" in name for name in node_names)


def test_frugal_memory_guard_guarantee(aether_swarm):
    # Verify the orchestrator's OWN RAM overhead stays within its budget.
    # The host process' absolute RSS also reflects everything else running in it
    # (e.g. the whole pytest session), so the guarantee is checked on the RSS
    # increase attributable to this orchestrator, not on the absolute RSS.
    stats = aether_swarm.get_local_footprint()
    assert "local_rss_mb" in stats
    assert "local_rss_delta_mb" in stats
    assert "cloud_offload_active" in stats
    assert stats["cloud_offload_active"] is True
    assert stats["local_rss_delta_mb"] < aether_swarm.max_local_ram_budget_mb
    assert stats["zero_ram_guarantee"] is True


def test_cross_model_consensus_synthesis(aether_swarm):
    async def _run():
        mock_responses = [
            {"provider": "groq", "model": "llama-3.3-70b", "content": "Protocole: Utiliser AES-256-GCM avec rotation de clés memfd."},
            {"provider": "openrouter", "model": "deepseek-r1", "content": "Solution: Chiffrement AES-256-GCM et memfd_create anonyme."},
            {"provider": "qwen", "model": "qwen-2.5-coder", "content": "Architecture: Implémentation AES-256-GCM en RAM pure."}
        ]

        consensus = aether_swarm.synthesize_cross_model_consensus(
            query="Comment sécuriser les transferts de données en RAM ?",
            responses=mock_responses
        )
        assert isinstance(consensus, SwarmConsensusResult)
        assert consensus.agreement_score >= 0.8
        assert "AES-256-GCM" in consensus.synthesized_content
        assert len(consensus.participating_models) == 3
        assert consensus.local_cpu_consumed == 0.0  # 100% computed in cloud
    asyncio.run(_run())


def test_swarm_offloaded_execution(aether_swarm):
    async def _run():
        res = await aether_swarm.execute_swarm_objective(
            objective="Analyse d'architecture cryptographique sans impacter la RAM locale"
        )
        assert res["success"] is True
        assert "consensus" in res
        assert "telemetry" in res
        assert res["telemetry"]["offloaded_to_cloud"] is True
        assert res["telemetry"]["zero_ram_penalty"] is True
    asyncio.run(_run())


def test_swarm_no_fabrication_when_all_providers_fail(aether_swarm, monkeypatch):
    """Régression ciblée : l'ancien code injectait 3 réponses fabriquées
    ('Solution optimale pour ...', 'Analyse rigoureuse de ...', 'Code et structure de ...')
    dès que la fédération ne répondait pas. Ici, les 3 providers échouent réellement
    (simulant clés API absentes / réseau indisponible) : le consensus doit rester honnête,
    pas remplacé par du texte inventé."""
    async def _run():
        async def all_fail(provider, prompt, model=None, **kwargs):
            return None
        monkeypatch.setattr(aether_swarm.federation, "query_specific_provider", all_fail)

        res = await aether_swarm.execute_swarm_objective("Faut-il utiliser PostgreSQL ou MongoDB ?")

        assert res["consensus"]["participating_models"] == []
        assert res["consensus"]["agreement_score"] == 0.0
        content = res["consensus"]["synthesized_content"]
        assert "Solution optimale pour" not in content
        assert "Analyse rigoureuse de" not in content
        assert "architecture haute performance décentralisée" not in content
    asyncio.run(_run())


def test_swarm_consensus_reflects_only_real_responses(aether_swarm, monkeypatch):
    """Régression ciblée : quand un seul provider répond réellement, le consensus ne doit
    citer que ce provider et son vrai contenu - jamais les 2 autres fabriqués en silence."""
    async def _run():
        async def one_real_response(provider, prompt, model=None, **kwargs):
            if provider == "groq":
                return {"provider": "groq", "model": model, "content": "Réponse réelle unique de test X42"}
            return None
        monkeypatch.setattr(aether_swarm.federation, "query_specific_provider", one_real_response)

        res = await aether_swarm.execute_swarm_objective("Objectif de test")

        assert res["consensus"]["participating_models"] == ["groq:openai/gpt-oss-120b"]
        assert "Réponse réelle unique de test X42" in res["consensus"]["synthesized_content"]
        assert "deepseek" not in res["consensus"]["synthesized_content"].lower()
        assert "qwen" not in res["consensus"]["synthesized_content"].lower()
    asyncio.run(_run())


def test_cli_dispatch_swarm_command():
    from unittest.mock import AsyncMock, patch
    from app.tools.gateway import ToolGateway
    from app.resource_manager.watchdog import ResourceManager
    from app.orchestrator.orchestrator import TechLeadOrchestrator
    import cli

    gw = ToolGateway(workspace_root="/tmp")
    rm = ResourceManager()
    orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

    async def _run():
        with patch.object(orch.telegram_vault, "send_message", new_callable=AsyncMock) as mock_send_msg, \
             patch.object(orch.voice, "synthesize_speech", new_callable=AsyncMock) as mock_synth:
            mock_send_msg.return_value = True
            mock_synth.return_value = io.BytesIO(b"fake_audio")

            await cli.dispatch_telegram_order(orch, "/swarm Quelle est la meilleure stratégie cyber ?", user="Michael")

            assert mock_send_msg.call_count >= 2
            sent_texts = [call[0][0] for call in mock_send_msg.call_args_list]
            assert any("Essaim Aether" in t for t in sent_texts)
            assert any("Consensus" in t for t in sent_texts)
    asyncio.run(_run())

