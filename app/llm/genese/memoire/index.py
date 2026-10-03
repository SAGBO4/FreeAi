import sqlite3
import json

class IndexMemoire:
    """
    Index SQLite 100% en RAM pour respecter le Mode NÉANT.
    Gère les metadata des fragments (shards) et la lignée d'évolution.
    """
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS shards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie TEXT, -- fondation, general, eval, reve
                contenu TEXT,
                poids_importance REAL DEFAULT 1.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS lignee (
                version_id TEXT PRIMARY KEY,
                parent_id TEXT,
                genome_json TEXT,
                score_eval REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def ajouter_shard(self, categorie: str, contenu: str, importance: float = 1.0):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO shards (categorie, contenu, poids_importance) VALUES (?, ?, ?)", 
                    (categorie, contenu, importance))
        self.conn.commit()

    def obtenir_shards(self, categorie: str, limite: int = 100):
        cur = self.conn.cursor()
        cur.execute("SELECT contenu FROM shards WHERE categorie = ? ORDER BY timestamp DESC LIMIT ?", (categorie, limite))
        return [row[0] for row in cur.fetchall()]

    def enregistrer_version(self, version_id: str, parent_id: str, genome: dict, score: float):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO lignee (version_id, parent_id, genome_json, score_eval) VALUES (?, ?, ?, ?)",
                    (version_id, parent_id, json.dumps(genome), score))
        self.conn.commit()
