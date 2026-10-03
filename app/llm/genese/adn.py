import dataclasses

@dataclasses.dataclass
class ADNModele:
    vocab_size: int = 16384
    d_model: int = 384
    n_couches: int = 6
    n_tetes: int = 6
    contexte: int = 512
    stade: int = 0
    dense: bool = True
    nom: str = "jarvis-s0-v0001"
    
    @property
    def d_head(self):
        return self.d_model // self.n_tetes
