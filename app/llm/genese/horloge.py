import asyncio
import logging

logger = logging.getLogger(__name__)

class RythmeCatadien:
    """
    Ordonnanceur de tâches de Jarvis.
    Gère les phases d'éveil (inférence), consolidation nocturne (entraînement),
    et rêve génératif.
    """
    def __init__(self, consolidation_task=None):
        self.en_cours_de_consolidation = False
        self.consolidation_task = consolidation_task
        self._tache_fond = None

    async def demarrer_cycle(self, intervalle_heures: float = 24.0):
        """Lance l'horloge biologique de l'IA en arrière-plan."""
        import os
        from .bootstrap.distillateur import DistillateurBenchmark
        from .bootstrap.curriculum import CurriculumAdaptatif
        logger.info(f"[JARVIS] Démarrage du rythme catadien (cycle: {intervalle_heures}h)")
        
        curriculum = CurriculumAdaptatif()
        distillateur = DistillateurBenchmark()
        
        while True:
            # Phase d'éveil (Toutes les 2h : session bootstrap légère)
            if os.getenv("DEEPSEEK_API_KEY"):
                try:
                    cat_prio = await curriculum.prochaine_session()
                    logger.info(f"[JARVIS] Session Bootstrap (Eveil) sur la catégorie: {cat_prio}")
                    await distillateur.run_benchmark_session(n_prompts_par_categorie=5, categories=[cat_prio])
                    # Méta-apprentissage: simule un delta de perte pour l'exemple
                    curriculum.ajouter_perte(cat_prio, 0.5) 
                except Exception as e:
                    logger.debug(f"[JARVIS] Erreur Bootstrap: {e}")
                    
            await asyncio.sleep(intervalle_heures * 3600)
            await self.declencher_sommeil()

    async def declencher_sommeil(self):
        """Déclenche la phase de consolidation."""
        if self.en_cours_de_consolidation:
            return
            
        logger.info("[JARVIS] Entrée en phase de sommeil et consolidation...")
        self.en_cours_de_consolidation = True
        try:
            if self.consolidation_task:
                await self.consolidation_task()
        except Exception as e:
            logger.error(f"[JARVIS] Erreur durant le sommeil: {e}")
        finally:
            self.en_cours_de_consolidation = False
            logger.info("[JARVIS] Réveil. Phase d'éveil active.")
