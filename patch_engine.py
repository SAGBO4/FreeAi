import re

with open("app/llm/engine.py", "r") as f:
    content = f.read()

import_code = """
import torch
from .genese.adn import ADNModele
from .genese.tokenizer import TokenizerGenese
from .genese.modele import GeneseModele
from .genese.ame.gardien import GardienEthique

class GeneseCoreRuntime:
    \"\"\"Noyau Neural Natif GENÈSE (Stade 0).
    Opère en RAM pure (Mode NÉANT) et précède toute autre inférence.
    \"\"\"
    def __init__(self, model_path: str = "./models/genese-s0-v0001.pt"):
        self.model_path = Path(model_path)
        self.modele = None
        self.tokenizer = None
        self.gardien = GardienEthique()
        self.actif = False
        self._init_core()

    def _init_core(self):
        if self.model_path.exists() and self.model_path.is_file():
            try:
                self.tokenizer = TokenizerGenese()
                adn = ADNModele()
                self.modele = GeneseModele(adn)
                
                # Mode NÉANT : charge directement en RAM
                etat = torch.load(self.model_path, map_location='cpu', weights_only=True)
                self.modele.load_state_dict(etat)
                self.modele.eval()
                self.actif = True
                logger.info(f"[GENÈSE_CORE] Noyau neural natif chargé avec succès depuis {self.model_path}")
            except Exception as e:
                logger.error(f"[GENÈSE_CORE] Échec de l'éveil du noyau Genèse : {e}")

    async def generate_local(self, prompt: str, system_prompt: Optional[str] = None, max_new_tokens: int = 150, temperature: float = 0.7) -> Optional[str]:
        if not self.actif or self.modele is None:
            return None
            
        def _infer():
            # Combine system prompt
            full_prompt = f"<|systeme|>{system_prompt}<|utilisateur|>{prompt}<|genese|>" if system_prompt else f"<|utilisateur|>{prompt}<|genese|>"
            tokens = self.tokenizer.encode(full_prompt, add_special_tokens=True)
            input_ids = torch.tensor([tokens], dtype=torch.long)
            
            out_tokens = self.modele.generer(input_ids, max_new_tokens, temperature)
            gen_tokens = out_tokens[0][len(tokens):].tolist()
            
            texte = self.tokenizer.decode(gen_tokens)
            texte = self.gardien.filtrer(texte)
            return texte
            
        try:
            return await asyncio.to_thread(_infer)
        except Exception as e:
            logger.error(f"[GENÈSE_CORE] Erreur lors du raisonnement : {e}")
            return None

"""

# Insert GeneseCoreRuntime before LocalNeuralRuntime
content = re.sub(r'class LocalNeuralRuntime:', import_code + '\nclass LocalNeuralRuntime:', content, count=1)

# Add self.genese_runtime to FreeAIEngine.__init__
init_patch = """        self.local_runtime = LocalNeuralRuntime(model_path=model_path)
        self.genese_runtime = GeneseCoreRuntime()"""
content = re.sub(r'self\.local_runtime = LocalNeuralRuntime\(model_path=model_path\)', init_patch, content, count=1)

# Modify generate to use genese_runtime
generate_patch = """        # 0. Try Genese Native Core first
        genese_ans = await self.genese_runtime.generate_local(clean_p, system_prompt=system_prompt)
        if genese_ans:
            return genese_ans

        # 1. Try local neural model if available"""
content = re.sub(r'# 1\. Try local neural model if available', generate_patch, content, count=1)

# Enrich reason_and_plan_neural
reason_patch = """        if self.genese_runtime.actif:
            logger.info(f"[{self.name}] Raisonnement propulsé par le noyau natif GENÈSE.")
            
        sys_prompt = ("""
content = re.sub(r'sys_prompt = \(', reason_patch, content, count=1)

with open("app/llm/engine.py", "w") as f:
    f.write(content)

