#!/usr/bin/env python3
"""
Tests for SovereignSearchEngine & Multi-Tier Cloud Search Swarm.
Verifies:
- AC1: Tavily Search Provider (direct clean intelligence with API key)
- AC2: Local Sovereign Search Provider (DuckDuckGo + HTML sanitizer + HDC 256-D reranker)
- AC3: GitHub Actions Cloud Runner Provider (asynchronous offloaded crawling via gh CLI)
- AC4: SovereignSearchEngine automatic routing and failover
- AC5: AetherLegion integration with zero hardcoded strings
"""

import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.tools.sovereign_search import (
    SovereignSearchEngine,
    TavilySearchProvider,
    LocalSovereignProvider,
    GitHubActionsSearchProvider,
    SearchResultItem,
    SearchEngineResponse
)
from app.cluster.aether_legion import AetherLegionOrchestrator, ScoutArchetype


class TestSovereignSearchPipeline(unittest.TestCase):
    def setUp(self):
        self.engine = SovereignSearchEngine()

    def test_ac1_tavily_search_success(self):
        """AC1: Tavily provider parses API response into structured SearchEngineResponse."""
        provider = TavilySearchProvider(api_key="tvly-mock-key")
        mock_response = {
            "query": "CVE-2026 Linux vulnerability",
            "answer": "A critical Linux kernel privilege escalation vulnerability was discovered.",
            "results": [
                {
                    "title": "Linux Kernel Advisory 2026",
                    "url": "https://kernel.org/advisory",
                    "content": "Details on the buffer overflow in socket handling.",
                    "score": 0.96
                },
                {
                    "title": "NVD CVE Entry",
                    "url": "https://nvd.nist.gov/cve",
                    "content": "Vulnerability metrics and affected packages.",
                    "score": 0.88
                }
            ]
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_post.return_value = mock_resp

            async def _run():
                res = await provider.search("CVE-2026 Linux vulnerability", max_results=2)
                self.assertTrue(res.success)
                self.assertEqual(res.provider, "tavily")
                self.assertIn("critical Linux kernel", res.answer)
                self.assertEqual(len(res.results), 2)
                self.assertEqual(res.results[0].title, "Linux Kernel Advisory 2026")
                self.assertGreater(res.results[0].score, 0.9)
                self.assertFalse(res.simulated)

            asyncio.run(_run())

    def test_ac2_local_sanitizer_and_hdc_reranker(self):
        """AC2: Local provider cleans HTML noise and ranks passages using HDC semantic similarity."""
        provider = LocalSovereignProvider()
        raw_html = """
        <html>
            <head><title>Linux Kernel Security Patch</title></head>
            <body>
                <nav><a href="/home">Home</a> <a href="/ads">Buy Crypto</a></nav>
                <div class="cookie-banner">Please accept all cookies</div>
                <article>
                    <h1>Critical Fix in Network Stack</h1>
                    <p>A race condition in the Linux network namespace code was fixed.</p>
                    <p>Attackers could bypass memory isolation using crafted packet descriptors.</p>
                </article>
                <footer>Copyright 2026 Spam Inc</footer>
            </body>
        </html>
        """
        clean_text = provider.sanitize_html(raw_html)
        self.assertNotIn("cookie-banner", clean_text.lower())
        self.assertNotIn("buy crypto", clean_text.lower())
        self.assertIn("race condition in the linux network namespace", clean_text.lower())

        # Test HDC Reranking
        passages = [
            "Recipe for chocolate cake with strawberry frosting.",
            "Linux kernel security advisory regarding network namespace memory corruption.",
            "The weather in Tokyo is sunny today."
        ]
        scored = provider.rerank_passages("kernel security vulnerability", passages)
        self.assertEqual(len(scored), 3)
        # Most relevant passage should have highest score
        self.assertIn("network namespace", scored[0]["text"].lower())
        self.assertGreater(scored[0]["score"], scored[1]["score"])

    def test_ac3_github_actions_workflow_dispatch_spec(self):
        """AC3: GitHub Actions provider constructs valid gh workflow dispatch arguments."""
        gh_provider = GitHubActionsSearchProvider(repo="SAGBO4/FreeAi")

        with patch("shutil.which", return_value="/usr/bin/gh"), \
             patch("asyncio.create_subprocess_exec") as mock_exec:

            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            async def _run():
                res = await gh_provider.dispatch_crawler_job("quantum computing research", max_urls=5)
                self.assertTrue(res["success"])
                self.assertEqual(res["workflow"], "sovereign_crawler.yml")
                self.assertEqual(res["repo"], "SAGBO4/FreeAi")
                # Ensure gh workflow run was called
                args = mock_exec.call_args[0]
                self.assertIn("gh", args)
                self.assertIn("workflow", args)
                self.assertIn("run", args)
                self.assertIn("sovereign_crawler.yml", args)

            asyncio.run(_run())

    def test_ac4_engine_automatic_tier_selection(self):
        """AC4: SovereignSearchEngine routes to Tavily when available and falls back to local."""
        # Scenario A: Tavily key present -> routes to Tavily
        with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-test-123"}):
            engine = SovereignSearchEngine()
            self.assertEqual(engine.get_optimal_tier("recherche rapide"), "tavily")

        # Scenario B: No Tavily key -> falls back to local
        with patch.dict(os.environ, {}, clear=True):
            engine_no_key = SovereignSearchEngine()
            engine_no_key.tavily_key = None
            self.assertEqual(engine_no_key.get_optimal_tier("recherche rapide"), "local")

    def test_ac5_aether_legion_zero_hardcoded_strings(self):
        """AC5: AetherLegion uses real search findings without static hardcoded strings."""
        legion = AetherLegionOrchestrator()
        scout = legion.deploy_scout(
            name="Scout-Real-Test",
            archetype=ScoutArchetype.SINGULARITY,
            mission="Dernières avancées sur les réseaux de neurones distribués"
        )

        mock_search_result = SearchEngineResponse(
            query="Dernières avancées",
            provider="tavily",
            answer="Nouvelle méthode de parallélisme tensoriel",
            results=[
                SearchResultItem(
                    title="Real Paper Title 2026",
                    url="https://arxiv.org/abs/2601.12345",
                    content="Breakthrough in zero-latency tensor streaming.",
                    score=0.92
                )
            ],
            success=True,
            simulated=False
        )

        with patch("app.tools.sovereign_search.SovereignSearchEngine.search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_search_result

            async def _run():
                recon = await legion.execute_recon_mission(scout.id)
                self.assertTrue(recon["success"])
                self.assertEqual(len(recon["findings"]), 1)
                finding = recon["findings"][0]
                # Finding must contain real scraped data
                self.assertEqual(finding["headline"], "Real Paper Title 2026")
                self.assertEqual(finding["source"], "https://arxiv.org/abs/2601.12345")
                self.assertIn("Breakthrough in zero-latency", finding["summary"])

            asyncio.run(_run())

    def test_ac6_resilience_tavily_outage_fallback_to_local(self):
        """AC6: Resilience under breakage: Tavily 500 error / timeout triggers seamless fallback to local tier."""
        engine = SovereignSearchEngine(tavily_key="tvly-mock-broken-key")
        local_mock_response = SearchEngineResponse(
            query="failover test",
            provider="local",
            answer="Fallback local answer",
            results=[SearchResultItem(title="Local Result", url="https://local.org", content="Content", score=0.8)],
            success=True,
            simulated=False
        )

        with patch.object(engine.tavily, "search", new_callable=AsyncMock) as mock_tavily_search, \
             patch.object(engine.local, "search", new_callable=AsyncMock) as mock_local_search:
            mock_tavily_search.return_value = SearchEngineResponse(
                query="failover test",
                provider="tavily",
                answer="",
                results=[],
                success=False,
                telemetry={"error": "500 Internal Server Error"}
            )
            mock_local_search.return_value = local_mock_response

            async def _run():
                res = await engine.search("failover test", tier="auto")
                self.assertTrue(res.success)
                self.assertEqual(res.provider, "local")
                self.assertEqual(len(res.results), 1)
                self.assertEqual(res.results[0].title, "Local Result")
                mock_tavily_search.assert_called_once()
                mock_local_search.assert_called_once()

            asyncio.run(_run())

    def test_ac7_resilience_missing_key_direct_local_execution(self):
        """AC7: Zero API key scenario cleanly executes local search without crash or Tavily attempt."""
        engine = SovereignSearchEngine(tavily_key="")
        engine._tavily_key = ""

        with patch.object(engine.tavily, "search", new_callable=AsyncMock) as mock_tavily_search, \
             patch.object(engine.local, "search", new_callable=AsyncMock) as mock_local_search:
            mock_local_search.return_value = SearchEngineResponse(
                query="local query",
                provider="local",
                answer="DuckDuckGo HDC ranked",
                results=[],
                success=True
            )

            async def _run():
                res = await engine.search("local query", tier="auto")
                self.assertTrue(res.success)
                self.assertEqual(res.provider, "local")
                mock_tavily_search.assert_not_called()
                mock_local_search.assert_called_once()

            asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
