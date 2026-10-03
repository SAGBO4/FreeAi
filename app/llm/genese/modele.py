import math
import torch
import torch.nn as nn
from torch.nn import functional as F
from .adn import ADNModele

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x * norm * self.weight

def precompute_freqs_cis(dim: int, end: int, theta: float = 10000.0):
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    t = torch.arange(end, device=freqs.device, dtype=torch.float32)
    freqs = torch.outer(t, freqs).float()
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)
    return freqs_cis

def apply_rotary_emb(xq, xk, freqs_cis):
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))
    freqs_cis = freqs_cis.unsqueeze(0).unsqueeze(2)
    xq_out = torch.view_as_real(xq_ * freqs_cis).flatten(3)
    xk_out = torch.view_as_real(xk_ * freqs_cis).flatten(3)
    return xq_out.type_as(xq), xk_out.type_as(xk)

class SwiGLU(nn.Module):
    def __init__(self, in_features, hidden_features):
        super().__init__()
        self.w1 = nn.Linear(in_features, hidden_features, bias=False)
        self.w2 = nn.Linear(hidden_features, in_features, bias=False)
        self.w3 = nn.Linear(in_features, hidden_features, bias=False)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))

class CausalAttention(nn.Module):
    def __init__(self, adn: ADNModele):
        super().__init__()
        self.n_tetes = adn.n_tetes
        self.d_head = adn.d_head
        self.wq = nn.Linear(adn.d_model, adn.d_model, bias=False)
        self.wk = nn.Linear(adn.d_model, adn.d_model, bias=False)
        self.wv = nn.Linear(adn.d_model, adn.d_model, bias=False)
        self.wo = nn.Linear(adn.d_model, adn.d_model, bias=False)

    def forward(self, x, freqs_cis, mask=None):
        B, T, C = x.shape
        q = self.wq(x).view(B, T, self.n_tetes, self.d_head)
        k = self.wk(x).view(B, T, self.n_tetes, self.d_head)
        v = self.wv(x).view(B, T, self.n_tetes, self.d_head)

        q, k = apply_rotary_emb(q, k, freqs_cis[:T])
        
        q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
        
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(k.size(-1)))
        if mask is not None:
            att = att.masked_fill(mask[:T, :T] == 0, float('-inf'))
            
        att = F.softmax(att, dim=-1)
        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.wo(y)

class BlocJarvis(nn.Module):
    def __init__(self, adn: ADNModele):
        super().__init__()
        self.attention = CausalAttention(adn)
        self.ffn = SwiGLU(adn.d_model, int(adn.d_model * 4 * 2/3))
        self.norm1 = RMSNorm(adn.d_model)
        self.norm2 = RMSNorm(adn.d_model)

    def forward(self, x, freqs_cis, mask):
        x = x + self.attention(self.norm1(x), freqs_cis, mask)
        x = x + self.ffn(self.norm2(x))
        return x

class JarvisModele(nn.Module):
    def __init__(self, adn: ADNModele):
        super().__init__()
        self.adn = adn
        self.embeddings = nn.Embedding(adn.vocab_size, adn.d_model)
        self.couches = nn.ModuleList([BlocJarvis(adn) for _ in range(adn.n_couches)])
        self.norm_finale = RMSNorm(adn.d_model)
        self.sortie = nn.Linear(adn.d_model, adn.vocab_size, bias=False)
        self.sortie.weight = self.embeddings.weight # Weight tying
        
        self.freqs_cis = precompute_freqs_cis(adn.d_head, adn.contexte * 2)
        self.register_buffer("mask", torch.tril(torch.ones(adn.contexte, adn.contexte)).view(1, 1, adn.contexte, adn.contexte))

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, tokens, max_len=None):
        B, T = tokens.shape
        x = self.embeddings(tokens)
        freqs_cis = self.freqs_cis.to(x.device)
        mask = self.mask.to(x.device)

        for couche in self.couches:
            x = couche(x, freqs_cis, mask)

        x = self.norm_finale(x)
        logits = self.sortie(x)
        return logits

    @torch.no_grad()
    def generer(self, tokens, max_new_tokens, temperature=1.0):
        for _ in range(max_new_tokens):
            if tokens.size(1) > self.adn.contexte:
                tokens = tokens[:, -self.adn.contexte:]
            logits = self(tokens)[:, -1, :]
            if temperature == 0.0:
                _, next_token = torch.topk(logits, 1, dim=-1)
            else:
                logits = logits / temperature
                probs = F.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            tokens = torch.cat((tokens, next_token), dim=1)
        return tokens
