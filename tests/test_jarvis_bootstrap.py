import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.llm.genese.bootstrap.distillateur import DistillateurBenchmark
from app.llm.genese.bootstrap.curriculum import CurriculumAdaptatif
from app.llm.genese.bootstrap.evaluateur import EvaluateurConsensus

@pytest.fixture
def distillateur():
    return DistillateurBenchmark()

@pytest.fixture
def curriculum():
    return CurriculumAdaptatif()

@pytest.fixture
def evaluateur():
    return EvaluateurConsensus()

def test_distillateur_run_benchmark_session(distillateur):
    with patch("app.llm.genese.bootstrap.distillateur.os.getenv", return_value="fake-key"):
        from unittest.mock import AsyncMock
        with patch("app.llm.genese.bootstrap.distillateur.DistillateurBenchmark._query_professeur", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = [
                '{"prompts": ["Q1", "Q2"]}', 
                "Reponse 1", 
                "Reponse 1", 
                "Reponse 2", 
                "Contradiction faux impossible" 
            ]
            
            stats = asyncio.run(distillateur.run_benchmark_session(n_prompts_par_categorie=2, categories=["code_python"]))
            assert "categories" in stats
            assert "code_python" in stats["categories"]
            assert stats["total_generes"] == 2

def test_curriculum_adaptatif(curriculum):
    curriculum.ajouter_perte("code_python", 2.0)
    curriculum.ajouter_perte("code_python", 1.8) # Baisse de >0.05
    
    curriculum.ajouter_perte("mathematiques", 0.4)
    curriculum.ajouter_perte("mathematiques", 0.3) # Maitrisé (<0.5)
    
    priorites = curriculum.calculer_priorites()
    
    assert priorites.get("code_python", 1.0) > 1.0 # Progrès rapide => Augmente prio
    assert priorites.get("mathematiques", 1.0) < 1.0 # Maitrisé => Baisse prio

def test_evaluateur_consensus(evaluateur):
    score_haut = evaluateur.calculer_consensus("Le ciel est bleu et clair", "Le ciel est bleu, très clair")
    assert score_haut > 0.6
    
    score_bas = evaluateur.calculer_consensus("Totalement faux et impossible", "Ceci est une vérité absolue")
    assert score_bas < 0.6 # Due to contradictions and zero common words
