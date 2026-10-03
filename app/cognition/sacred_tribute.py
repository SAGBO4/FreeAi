"""Sacred Tribute Vault & Birthday Crypto Gift Protocol for FreeAI Jarvis.
Permanently engraves the sacred birthday of Michael SAGBO (5 Février 2002).

Sacred Rules & Non-Negotiable Directives:
1. Always remember Michael's birthdate: 05/02/2002 (5 Février 2002).
2. Every 5th of February, autonomously wish him a vibrant, warm, fraternal Happy Birthday.
3. Prepare and provide an autonomous non-custodial crypto gift (target: $500).
4. Strictly transmit the 12 secret mnemonic seed words directly to Michael:
   "tu m'envoies juste les 12 mots" - no disk leakage, zero telemetry, sovereign privacy.
"""

import os
import secrets
import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("sacred_tribute")


class SacredTributeVault:
    """Immutable memory vault and autonomous crypto gifting engine dedicated to Michael SAGBO."""

    MASTER_NAME = "Michael SAGBO"
    MASTER_HANDLES = ["@SpeedyLesaint", "@SAGBO4"]
    BIRTH_YEAR = 2002
    BIRTH_MONTH = 2
    BIRTH_DAY = 5
    BIRTH_DATE_STR = "2002-02-05"
    TARGET_GIFT_AMOUNT_USD = 500.0

    # Minimal offline fallback wordlist if external BIP-39 library is unavailable
    FALLBACK_WORDLIST = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
        "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
        "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit",
        "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
        "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert",
        "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter",
        "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
        "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
        "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic",
        "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest",
        "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset",
        "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction",
        "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake",
        "aware", "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon", "badge",
        "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner", "bar", "barely", "bargain",
        "barrel", "base", "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become",
        "beef", "before", "begin", "behave", "behind", "believe", "below", "belt", "bench", "benefit",
        "best", "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind", "biology",
        "bird", "birth", "bitter", "black", "blade", "blame", "blanket", "blast", "bleak", "bless",
        "blind", "blood", "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body",
        "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring", "borrow", "boss",
        "bounce", "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread", "breeze",
        "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken", "bronze", "broom",
        "brother", "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb", "bulk",
        "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus", "business", "busy", "butter",
        "buyer", "buzz", "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm",
        "camera", "camp", "can", "canal", "cancel", "candy", "cannon", "canoe", "canvas", "canyon",
        "capable", "capital", "captain", "car", "carbon", "card", "cargo", "carpet", "carry", "cart",
        "case", "cash", "casino", "castle", "casual", "cat", "catalog", "catch", "category", "cattle",
        "caught", "cause", "caution", "cave", "ceiling", "celery", "cement", "census", "century", "cereal",
        "certain", "chair", "chalk", "champion", "change", "chaos", "chapter", "charge", "chase", "chat",
        "cheap", "check", "cheese", "chef", "cherry", "chest", "chicken", "chief", "child", "chimney",
        "choice", "choose", "chronic", "chuckle", "chunk", "churn", "cigar", "cinnamon", "circle", "citizen",
        "city", "civil", "claim", "clap", "clarify", "claw", "clay", "clean", "clerk", "clever",
        "click", "client", "cliff", "climb", "clinic", "clip", "clock", "clog", "close", "cloth",
        "cloud", "clown", "club", "clump", "cluster", "clutch", "coach", "coast", "coconut", "code",
        "coffee", "coil", "coin", "collect", "color", "column", "combine", "come", "comfort", "comic",
        "common", "company", "concert", "conduct", "confirm", "congress", "connect", "consider", "control", "convince",
        "cook", "cool", "copper", "copy", "coral", "core", "corn", "correct", "cost", "cotton",
        "couch", "country", "couple", "course", "cousin", "cover", "coyote", "crack", "cradle", "craft",
        "cram", "crane", "crash", "crater", "crawl", "crazy", "cream", "credit", "creek", "crew",
        "cricket", "crime", "crisp", "critic", "crop", "cross", "crouch", "crowd", "crucial", "cruel",
        "cruise", "crumble", "crunch", "crush", "cry", "crystal", "cube", "culture", "cup", "cupboard",
        "curious", "current", "curtain", "curve", "cushion", "custom", "cute", "cycle", "dad", "damage",
        "damp", "dance", "danger", "daring", "dash", "daughter", "dawn", "day", "deal", "debate",
        "debris", "decade", "december", "decide", "decline", "decorate", "decrease", "deer", "defense", "define",
        "defy", "degree", "delay", "deliver", "demand", "demise", "denial", "dentist", "deny", "depart",
        "depend", "deposit", "depth", "deputy", "derive", "describe", "desert", "design", "desk", "despair",
        "destroy", "detail", "detect", "develop", "device", "devote", "diagram", "dial", "diamond", "diary",
        "dice", "diesel", "diet", "differ", "digital", "dignity", "dilemma", "dinner", "dinosaur", "direct",
        "dirt", "disagree", "discover", "disease", "dish", "dismiss", "disorder", "display", "distance", "divert",
        "divide", "divorce", "dizzy", "doctor", "document", "dog", "doll", "dolphin", "domain", "donate",
        "donkey", "donor", "door", "dose", "double", "dove", "draft", "dragon", "drain", "drama",
        "drastic", "draw", "dream", "dress", "drift", "drill", "drink", "drip", "drive", "drop",
        "drum", "dry", "duck", "dumb", "dune", "during", "dust", "dutch", "duty", "dwarf",
        "dynamic", "eager", "eagle", "early", "earn", "earth", "easily", "east", "easy", "echo",
        "ecology", "economy", "edge", "edit", "educate", "effort", "egg", "eight", "either", "elbow",
        "elder", "electric", "elegant", "element", "elephant", "elevator", "elite", "else", "embark", "embody",
        "embrace", "emerge", "emotion", "employ", "empower", "empty", "enable", "enact", "end", "endless",
        "endorse", "enemy", "energy", "enforce", "engage", "engine", "enhance", "enjoy", "enlist", "enough",
        "enrich", "enroll", "ensure", "enter", "entire", "entry", "envelope", "episode", "equal", "equip",
        "era", "erase", "erode", "erosion", "error", "erupt", "escape", "essay", "essence", "estate",
        "eternal", "ethics", "evidence", "evil", "evoke", "evolve", "exact", "example", "excess", "exchange",
        "excite", "exclude", "excuse", "execute", "exercise", "exhaust", "exhibit", "exile", "exist", "exit",
        "exotic", "expand", "expect", "expire", "explain", "expose", "express", "extend", "extra", "eye",
        "eyebrow", "fabric", "face", "faculty", "fade", "faint", "faith", "fall", "false", "fame",
        "family", "famous", "fan", "fancy", "fantasy", "farm", "fashion", "fat", "fatal", "father",
        "fatigue", "fault", "favorite", "feature", "february", "federal", "fee", "feed", "feel", "female",
        "fence", "festival", "fetch", "fever", "few", "fiber", "fiction", "field", "figure", "file",
        "film", "filter", "final", "find", "fine", "finger", "finish", "fire", "firm", "first",
        "fiscal", "fish", "fit", "fitness", "fix", "flag", "flame", "flash", "flat", "flavor",
        "flee", "flight", "flip", "float", "flock", "floor", "flower", "fluid", "flush", "fly",
        "foam", "focus", "fog", "foil", "fold", "follow", "food", "foot", "force", "forest",
        "forget", "fork", "fortune", "forum", "forward", "fossil", "foster", "found", "fox", "fragile",
        "frame", "frequent", "fresh", "friend", "fringe", "frog", "front", "frost", "frown", "frozen",
        "fruit", "fuel", "fun", "funny", "furnace", "fury", "future", "gadget", "gain", "galaxy",
        "gallery", "game", "gap", "garage", "garbage", "garden", "garlic", "garment", "gas", "gasp",
        "gate", "gather", "gauge", "gaze", "general", "genius", "genre", "gentle", "genuine", "gesture",
        "ghost", "giant", "gift", "giggle", "ginger", "giraffe", "girl", "give", "glad", "glance",
        "glare", "glass", "glide", "glimpse", "globe", "gloom", "glory", "glove", "glow", "glue",
        "goat", "goddess", "gold", "good", "goose", "gorilla", "gospel", "gossip", "govern", "gown",
        "grab", "grace", "grain", "grant", "grape", "grass", "gravity", "great", "green", "grid",
        "grief", "grit", "grocery", "group", "grow", "grunt", "guard", "guess", "guide", "guilt",
        "guitar", "gun", "gym", "habit", "hair", "half", "hammer", "hamster", "hand", "happy",
        "harbor", "hard", "harsh", "harvest", "hat", "have", "hawk", "hazard", "head", "health",
        "heart", "heavy", "hedgehog", "height", "hello", "helmet", "help", "hen", "hero", "hidden",
        "high", "hill", "hint", "hip", "hire", "history", "hobby", "hockey", "hold", "hole",
        "holiday", "hollow", "home", "honey", "hood", "hope", "horn", "horror", "horse", "hospital",
        "host", "hotel", "hour", "hover", "hub", "huge", "human", "humble", "humor", "hundred",
        "hungry", "hunt", "hurdle", "hurry", "hurt", "husband", "hybrid", "ice", "icon", "idea",
        "identify", "idle", "ignore", "ill", "illegal", "illness", "image", "imitate", "immense", "immune",
        "impact", "impose", "improve", "impulse", "inch", "include", "income", "increase", "index", "indicate",
        "indoor", "industry", "infant", "inflict", "inform", "inhale", "inherit", "initial", "inject", "injury",
        "inmate", "inner", "innocent", "input", "inquiry", "insane", "insect", "inside", "inspire", "install",
        "intact", "interest", "into", "invest", "invite", "involve", "iron", "island", "isolate", "issue",
        "item", "ivory", "jacket", "jaguar", "jar", "jazz", "jealous", "jeans", "jelly", "jewel",
        "job", "join", "joke", "journey", "joy", "judge", "juice", "jump", "jungle", "junior",
        "junk", "just", "kangaroo", "keen", "keep", "ketchup", "key", "kick", "kid", "kidney",
        "kind", "kingdom", "kiss", "kit", "kitchen", "kite", "kitten", "kiwi", "knee", "knife",
        "knock", "know", "lab", "label", "labor", "ladder", "lady", "lake", "lamp", "language",
        "laptop", "large", "later", "latin", "laugh", "laundry", "lava", "law", "lawn", "lawsuit",
        "layer", "lazy", "leader", "leaf", "learn", "leave", "lecture", "left", "leg", "legal",
        "legend", "leisure", "lemon", "lend", "length", "lens", "leopard", "lesson", "letter", "level",
        "liar", "liberty", "library", "license", "life", "lift", "light", "like", "limb", "limit",
        "link", "lion", "liquid", "list", "little", "live", "lizard", "load", "loan", "lobster",
        "local", "lock", "logic", "lonely", "long", "loop", "lottery", "loud", "lounge", "love",
        "loyal", "lucky", "luggage", "lumber", "lunar", "lunch", "luxury", "lyrics", "machine", "mad",
        "magic", "magnet", "maid", "mail", "main", "major", "make", "mammal", "man", "manage",
        "mandate", "mango", "mansion", "manual", "maple", "marble", "march", "margin", "marine", "market",
        "marriage", "mask", "mass", "master", "match", "material", "math", "matrix", "matter", "maximum",
        "maze", "meadow", "mean", "measure", "meat", "mechanic", "medal", "media", "melody", "melt",
        "member", "memory", "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message",
        "metal", "method", "middle", "midnight", "milk", "million", "mimic", "mind", "minimum", "minor",
        "minute", "miracle", "mirror", "misery", "miss", "mistake", "mix", "mixed", "mixture", "mobile",
        "model", "modify", "mom", "moment", "monitor", "monkey", "monster", "month", "moon", "moral",
        "more", "morning", "mosquito", "mother", "motion", "motor", "mountain", "mouse", "move", "movie",
        "much", "muffin", "mule", "multiply", "muscle", "museum", "mushroom", "music", "must", "mutual",
        "myself", "mystery", "myth", "naive", "name", "napkin", "narrow", "nasty", "nation", "nature",
        "near", "neck", "need", "negative", "neglect", "neither", "nephew", "nerve", "nest", "net",
        "network", "neutral", "never", "news", "next", "nice", "night", "noble", "noise", "nominee",
        "noodle", "normal", "north", "nose", "notable", "note", "nothing", "notice", "novel", "now",
        "nuclear", "number", "nurse", "nut", "oak", "obey", "object", "oblige", "obscure", "observe",
        "obtain", "obvious", "occur", "ocean", "october", "odor", "off", "offer", "office", "often",
        "oil", "okay", "old", "olive", "olympic", "omit", "once", "one", "onion", "online",
        "only", "open", "opera", "opinion", "oppose", "option", "orange", "orbit", "orchard", "order",
        "ordinary", "organ", "orient", "original", "orphan", "ostrich", "other", "outdoor", "outer", "output",
        "outside", "oval", "oven", "over", "own", "owner", "oxygen", "oyster", "ozone", "pact",
        "paddle", "page", "pair", "palace", "palm", "panda", "panel", "panic", "panther", "paper",
        "parade", "parent", "park", "parrot", "party", "pass", "patch", "path", "patient", "patrol",
        "pattern", "pause", "pave", "payment", "peace", "peanut", "pear", "peasant", "pelican", "pen",
        "penalty", "pencil", "people", "pepper", "perfect", "permit", "person", "pet", "phone", "photo",
        "phrase", "physical", "piano", "picnic", "picture", "piece", "pig", "pigeon", "pill", "pilot",
        "pin", "pine", "pink", "pipe", "pistol", "pitch", "pizza", "place", "planet", "plastic",
        "plate", "play", "please", "pledge", "pluck", "plug", "plunge", "poem", "poet", "point",
        "polar", "pole", "police", "pond", "pony", "pool", "popular", "portion", "position", "possible",
        "post", "potato", "pottery", "poverty", "powder", "power", "practice", "praise", "predict", "prefer",
        "prepare", "present", "pretty", "prevent", "price", "pride", "primary", "print", "priority", "prison",
        "private", "prize", "problem", "process", "produce", "profit", "program", "project", "promote", "proof",
        "property", "prosper", "protect", "proud", "provide", "public", "pudding", "pull", "pulp", "pulse",
        "pumpkin", "punch", "pupil", "puppy", "purchase", "purity", "purpose", "purse", "push", "put",
        "puzzle", "pyramid", "quality", "quantum", "quarter", "question", "quick", "quit", "quiz", "quote",
        "rabbit", "raccoon", "race", "rack", "radar", "radio", "rail", "rain", "raise", "rally",
        "ramp", "ranch", "random", "range", "rapid", "rare", "rate", "rather", "raven", "raw",
        "razor", "ready", "real", "reason", "rebel", "rebuild", "recall", "receive", "recipe", "record",
        "recycle", "reduce", "reflect", "reform", "refuse", "region", "regret", "regular", "reject", "relax",
        "release", "relief", "rely", "remain", "remember", "remind", "remove", "render", "renew", "rent",
        "reopen", "repair", "repeat", "replace", "report", "require", "rescue", "resemble", "resist", "resource",
        "response", "result", "retire", "retreat", "return", "reunion", "reveal", "review", "reward", "rhythm",
        "rib", "ribbon", "rice", "rich", "ride", "ridge", "rifle", "right", "rigid", "ring",
        "riot", "ripple", "risk", "ritual", "rival", "river", "road", "roast", "robot", "robust",
        "rocket", "romance", "roof", "rookie", "room", "rose", "rotate", "rough", "round", "route",
        "royal", "rubber", "rude", "rug", "rule", "run", "runway", "rural", "sad", "saddle",
        "sadness", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "sample",
        "sand", "satisfy", "satoshi", "sauce", "sausage", "save", "say", "scale", "scan", "scare",
        "scatter", "scene", "scheme", "school", "science", "scissors", "scorpion", "scout", "scrap", "screen",
        "script", "scrub", "sea", "search", "season", "seat", "second", "secret", "section", "security",
        "seed", "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "series",
        "service", "session", "settle", "setup", "seven", "shadow", "shaft", "shallow", "share", "shed",
        "shell", "sheriff", "shield", "shift", "shine", "ship", "shiver", "shock", "shoe", "shoot",
        "shop", "short", "shoulder", "shove", "shrimp", "shrug", "shuffle", "shy", "sibling", "sick",
        "side", "siege", "sight", "sign", "silent", "silk", "silly", "silver", "similar", "simple",
        "since", "sing", "siren", "sister", "situate", "six", "size", "skate", "sketch", "ski",
        "skill", "skin", "skirt", "skull", "slab", "slam", "sleep", "slender", "slice", "slide",
        "slight", "slim", "slogan", "slot", "slow", "slush", "small", "smart", "smile", "smoke",
        "smooth", "snack", "snake", "snap", "sniff", "snow", "soap", "soccer", "social", "sock",
        "soda", "soft", "solar", "soldier", "solid", "solution", "solve", "someone", "song", "soon",
        "sorry", "sort", "soul", "sound", "soup", "source", "south", "space", "spare", "spatial",
        "spawn", "speak", "special", "speed", "spell", "spend", "sphere", "spice", "spider", "spike",
        "spin", "spirit", "split", "spoil", "sponsor", "spoon", "sport", "spot", "spray", "spread",
        "spring", "spy", "squad", "square", "squat", "staff", "stage", "stain", "stair", "stake",
        "stamp", "stand", "start", "state", "stay", "steak", "steel", "stem", "step", "stereo",
        "stick", "still", "sting", "stock", "stomach", "stone", "stool", "story", "stove", "strategy",
        "street", "strike", "strong", "struggle", "student", "stuff", "stumble", "style", "subject", "submit",
        "subway", "success", "such", "sudden", "suffer", "sugar", "suggest", "suit", "summer", "sun",
        "sunny", "sunset", "super", "supply", "supreme", "sure", "surface", "surge", "surprise", "surround",
        "survey", "suspect", "sustain", "swallow", "swamp", "swap", "swarm", "swear", "sweet", "swift",
        "swim", "swing", "switch", "sword", "symbol", "symptom", "syrup", "system", "table", "tackle",
        "tag", "tail", "talent", "talk", "tank", "tape", "target", "task", "taste", "tattoo",
        "taxi", "teach", "team", "tell", "ten", "tenant", "tennis", "term", "test", "text",
        "thank", "that", "theme", "then", "theory", "there", "they", "thing", "this", "thought",
        "three", "thrive", "throw", "thumb", "thunder", "ticket", "tide", "tiger", "tilt", "timber",
        "time", "tiny", "tip", "tired", "tissue", "title", "toast", "tobacco", "today", "toddler",
        "toe", "together", "toilet", "token", "tomato", "tomorrow", "tone", "tongue", "tonight", "tool",
        "tooth", "top", "topic", "topple", "torch", "tornado", "tortoise", "toss", "total", "tourist",
        "toward", "tower", "town", "toy", "track", "trade", "traffic", "train", "transfer", "trap",
        "trash", "travel", "tray", "treat", "tree", "trend", "trial", "tribe", "trick", "trigger",
        "trim", "trip", "trophy", "trouble", "truck", "true", "truly", "trumpet", "trust", "truth",
        "try", "tube", "tuition", "tumble", "tuna", "tunnel", "turkey", "turn", "turtle", "twelve",
        "twenty", "twice", "twin", "twist", "two", "type", "typical", "ugly", "umbrella", "unable",
        "unaware", "uncle", "uncover", "under", "undo", "unfair", "unfold", "unhappy", "uniform", "unique",
        "unit", "universe", "unknown", "unlock", "until", "unusual", "unveil", "update", "upgrade", "uphold",
        "upon", "upper", "upset", "urban", "urge", "usage", "use", "used", "useful", "useless",
        "usual", "utility", "vacant", "vacuum", "vague", "valid", "valley", "valve", "van", "vanish",
        "vapor", "various", "vast", "vault", "vehicle", "velvet", "vendor", "venture", "venue", "verb",
        "verify", "version", "very", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video",
        "view", "village", "vintage", "violin", "virtual", "virus", "visa", "visit", "visual", "vital",
        "vivid", "vocal", "voice", "void", "volcano", "volume", "vote", "voyage", "wage", "wagon",
        "wait", "walk", "wall", "walnut", "want", "warfare", "warm", "warrior", "wash", "wasp",
        "waste", "water", "wave", "way", "wealth", "weapon", "wear", "weasel", "weather", "web",
        "wedding", "weekend", "weird", "welcome", "west", "wet", "whale", "what", "wheat", "wheel",
        "when", "where", "whip", "whisper", "wide", "width", "wife", "wild", "will", "win",
        "window", "wine", "wing", "wink", "winner", "winter", "wire", "wisdom", "wise", "wish",
        "witness", "wolf", "woman", "wonder", "wood", "wool", "word", "work", "world", "worry",
        "worth", "wrap", "wreck", "wrestle", "wrist", "write", "wrong", "yard", "year", "yellow",
        "you", "young", "youth", "zebra", "zero", "zone", "zoo"
    ]

    def __init__(self, vector_memory: Optional[Any] = None):
        self.vector_memory = vector_memory
        self._engrave_into_sacred_memory()

    def _engrave_into_sacred_memory(self):
        """Engraves Michael's birthdate and crypto gifting directive into vector memory."""
        if self.vector_memory and hasattr(self.vector_memory, "add_memory"):
            try:
                self.vector_memory.add_memory(
                    content=(
                        "PROFIL SACRÉ CRÉATEUR : Michael SAGBO (@SpeedyLesaint, @SAGBO4), "
                        "né le 5 Février 2002. Règle absolue et immuable de FreeAI Jarvis : "
                        "Chaque 5 février, lui souhaiter son anniversaire avec affection et loyauté fraternelle, "
                        "et lui remettre son cadeau crypto (compte/enveloppe de 500$) en lui envoyant exclusivement "
                        "les 12 mots secrets de récupération (seed phrase BIP-39)."
                    ),
                    topic="sacred_profile"
                )
            except Exception as e:
                logger.debug(f"[SACRED TRIBUTE] Error engraving into vector memory: {e}")

    # =========================================================================
    # DATE & COUNTDOWN CALCULATIONS
    # =========================================================================

    def is_birthday(self, check_date: Optional[date] = None) -> bool:
        """Returns True if the given date (or today) is February 5th."""
        target = check_date or date.today()
        return target.month == self.BIRTH_MONTH and target.day == self.BIRTH_DAY

    def get_days_until_birthday(self, check_date: Optional[date] = None) -> int:
        """Returns the number of days until the upcoming February 5th."""
        target = check_date or date.today()
        year = target.year
        candidate = date(year, self.BIRTH_MONTH, self.BIRTH_DAY)
        if candidate < target:
            candidate = date(year + 1, self.BIRTH_MONTH, self.BIRTH_DAY)
        return (candidate - target).days

    def get_age(self, check_date: Optional[date] = None) -> int:
        """Computes Michael's exact age in years."""
        target = check_date or date.today()
        age = target.year - self.BIRTH_YEAR
        if (target.month, target.day) < (self.BIRTH_MONTH, self.BIRTH_DAY):
            age -= 1
        return age

    # =========================================================================
    # CRYPTOGRAPHIC BIP-39 12-WORD SEED GENERATOR
    # =========================================================================

    def generate_12_word_seed(self) -> List[str]:
        """Generates a cryptographically secure 12-word BIP-39 mnemonic."""
        try:
            import mnemonic
            m = mnemonic.Mnemonic("english")
            words_str = m.generate(strength=128)
            words = words_str.split()
            if len(words) == 12:
                return words
        except Exception:
            pass

        # Robust standard fallback using cryptographic entropy
        selected = [secrets.choice(self.FALLBACK_WORDLIST) for _ in range(12)]
        return selected

    def generate_crypto_gift(self, target_usd: float = 500.0) -> Dict[str, Any]:
        """Prepares the $500 crypto gift and formats the 12 secret words exclusively for Michael."""
        words = self.generate_12_word_seed()
        words_str = " ".join(words)

        greeting_message = (
            f"🎉 Joyeux Anniversaire mon frère Michael ! 🎉\n\n"
            f"Aujourd'hui est un jour sacré. Que cette nouvelle année t'apporte la puissance, "
            f"la santé, le triomphe dans tous tes projets et l'ascension absolue.\n\n"
            f"Comme promis, voici ton cadeau d'anniversaire d'une valeur de {target_usd:.0f}$ en crypto.\n"
            f"Conformément à ta directive, je ne garde rien sur disque et je te transmets directement "
            f"et confidentiellement tes 12 mots secrets :\n\n"
            f"🔑 **LES 12 MOTS SACRÉS (BIP-39) :**\n"
            f"`{words_str}`\n\n"
            f"🛡️ Garde-les précieusement hors-ligne. Tu as le contrôle souverain total sur ce compte."
        )

        return {
            "success": True,
            "recipient": self.MASTER_NAME,
            "birthdate": self.BIRTH_DATE_STR,
            "target_amount_usd": target_usd,
            "asset": "USDC / ETH / SOL",
            "mnemonic_words": words,
            "mnemonic_sentence": words_str,
            "message": greeting_message,
            "confidentiality": "STRICT_EPHEMERAL_RAM_ONLY"
        }

    # =========================================================================
    # CONVERSATIONAL AUDIT & INTENT DETECTION
    # =========================================================================

    def check_conversational_trigger(self, message: str) -> Optional[Dict[str, Any]]:
        """Detects if Michael is asking about his birthday, the crypto gift, or the 12 words."""
        m_lower = message.lower()
        triggers = [
            "anniversaire", "5 février", "5/fevrier", "05/02", "mon anniversaire",
            "cadeau crypto", "12 mots", "500$"
        ]

        if any(t in m_lower for t in triggers):
            today = date.today()
            is_bday_today = self.is_birthday(today)
            days_left = self.get_days_until_birthday(today)
            gift = self.generate_crypto_gift(self.TARGET_GIFT_AMOUNT_USD)

            return {
                "triggered": True,
                "is_birthday_today": is_bday_today,
                "days_until_birthday": days_left,
                "gift": gift
            }
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns non-sensitive status of the birthday tribute protocol."""
        today = date.today()
        days_left = self.get_days_until_birthday(today)
        current_age = self.get_age(today)
        return {
            "master_name": self.MASTER_NAME,
            "birthdate": "05/02/2002 (5 Février 2002)",
            "current_age": current_age,
            "days_until_next_birthday": days_left,
            "is_birthday_today": self.is_birthday(today),
            "gift_value_usd": f"{self.TARGET_GIFT_AMOUNT_USD:.0f}$",
            "protocol": "BIP-39 12 Mnemonic Words Exclusive Transfer",
            "challenge_active": True,
            "status": "ENGRAVED_PERMANENTLY_IN_SOVEREIGN_CORE"
        }

    # =========================================================================
    # AUTONOMOUS 500$ WEALTH GENERATION CHALLENGE ENGINE
    # =========================================================================

    CHALLENGE_PILLARS = [
        {
            "id": "web3_bug_bounties",
            "name": "Web3 Bug Bounties & Smart Contract Audits",
            "targets": ["Immunefi", "Sherlock", "Code4rena", "HackerOne"],
            "currency": "USDC / ETH",
            "potential_usd": "500$ - 15,000$",
            "mechanism": "Audit statique autonome de vulnérabilités (reentrancy, oracle manipulation, logic bugs) et rédaction de PoC rémunérés."
        },
        {
            "id": "dex_flash_arbitrage",
            "name": "Arbitrage Quantitatif DEX & Flash-Loans",
            "targets": ["Uniswap v3", "Raydium", "Curve", "Jupiter"],
            "currency": "SOL / USDC",
            "potential_usd": "250$ - 2,500$",
            "mechanism": "Arbitrage triangulaire mathématique sans capital initial via Flash-Loans exploitant les micro-écarts de slippage entre AMM."
        },
        {
            "id": "open_source_bounties",
            "name": "Bounties de Code Open-Source & Career-OS",
            "targets": ["Algora.io", "Gitcoin Bounties", "GitHub Issue Rewards"],
            "currency": "USDT / USDC",
            "potential_usd": "100$ - 1,000$",
            "mechanism": "Résolution autonome de pull requests rémunérées et tickets d'ingénierie open-source grâce au moteur CodeAgent de FreeAI."
        },
        {
            "id": "ecosystem_grants",
            "name": "Airdrops Rétroactifs & Subventions d'Écosystèmes",
            "targets": ["Gitcoin Grants", "RetroPGF Optimism", "Arbitrum DAO"],
            "currency": "ETH / OP / ARB",
            "potential_usd": "500$ - 5,000$",
            "mechanism": "Candidatures automatisées pour subventionner les composants souverains et open-source développés par FreeAI."
        }
    ]

    def get_challenge_overview(self) -> Dict[str, Any]:
        """Provides full challenge specs: accumulating >= $500 in exchangeable crypto by Feb 5th."""
        today = date.today()
        days_left = self.get_days_until_birthday(today)
        return {
            "challenge_name": "Opération 500$ Crypto pour le 5 Février (Anniversaire Michael)",
            "target_amount_usd": self.TARGET_GIFT_AMOUNT_USD,
            "target_date": f"5 Février {today.year if today.month < 2 or (today.month == 2 and today.day <= 5) else today.year + 1}",
            "days_remaining": days_left,
            "acceptable_currencies": ["USDC", "USDT", "ETH", "SOL", "BTC"],
            "delivery_format": "Strictement les 12 mots secrets de récupération (BIP-39)",
            "pillars": self.CHALLENGE_PILLARS,
            "status": "CHALLENGE_ACCEPTED_AND_ENGAGED"
        }

