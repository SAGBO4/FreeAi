from typing import List, Union

SPECIAL_TOKENS = ["<|debut|>", "<|fin|>", "<|utilisateur|>", "<|jarvis|>", "<|systeme|>", "<|souvenir|>"]

class TokenizerJarvis:
    """
    Tokenizer BPE pour Jarvis.
    Tente d'utiliser `tokenizers` ou `tiktoken`. Si non disponibles, utilise un fallback minimal en RAM.
    """
    def __init__(self, vocab_size: int = 16384):
        self.vocab_size = vocab_size
        self.special_tokens = SPECIAL_TOKENS
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        try:
            from tokenizers import Tokenizer
            from tokenizers.models import BPE
            from tokenizers.pre_tokenizers import ByteLevel
            from tokenizers.trainers import BpeTrainer

            self._backend = "tokenizers"
            self.tokenizer = Tokenizer(BPE(unk_token="<|unk|>"))
            self.tokenizer.pre_tokenizer = ByteLevel(add_prefix_space=False)
            # Dans un environnement de production, on chargerait un tokenizer pré-entraîné
            # Ici on utilise une simple initialisation pour pouvoir s'exécuter.
            trainer = BpeTrainer(special_tokens=self.special_tokens + ["<|unk|>"], vocab_size=self.vocab_size)
            self.tokenizer.train_from_iterator(["Ceci est un texte de genèse pour initialiser le tokenizer interne."], trainer=trainer)
            
        except ImportError:
            try:
                import tiktoken
                self._backend = "tiktoken"
                self.encoding = tiktoken.get_encoding("cl100k_base")
                self.special_to_id = {st: self.vocab_size - len(self.special_tokens) + i for i, st in enumerate(self.special_tokens)}
            except ImportError:
                self._backend = "fallback"
                self.char_to_id = {chr(i): i for i in range(256)}
                self.special_to_id = {st: 256 + i for i, st in enumerate(self.special_tokens)}

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        tokens = []
        if self._backend == "tokenizers":
            tokens = self.tokenizer.encode(text).ids
        elif self._backend == "tiktoken":
            tokens = self.encoding.encode(text)[:self.vocab_size - len(self.special_tokens)]
        else:
            tokens = [ord(c) if ord(c) < 256 else 0 for c in text]

        if add_special_tokens:
            debut_id = self.get_special_token_id("<|debut|>")
            fin_id = self.get_special_token_id("<|fin|>")
            tokens = [debut_id] + tokens + [fin_id]
        return tokens

    def decode(self, tokens: List[int]) -> str:
        if self._backend == "tokenizers":
            return self.tokenizer.decode(tokens)
        elif self._backend == "tiktoken":
            return self.encoding.decode([t for t in tokens if t < self.vocab_size - len(self.special_tokens)])
        else:
            return "".join([chr(t) for t in tokens if t < 256])
            
    def get_special_token_id(self, token: str) -> int:
        if self._backend == "tokenizers":
            return self.tokenizer.token_to_id(token)
        elif self._backend == "tiktoken" or self._backend == "fallback":
            return self.special_to_id.get(token, 0)
        return 0
