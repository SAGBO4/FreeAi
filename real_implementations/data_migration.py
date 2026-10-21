import json
import os
import logging
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("FREEAI_CLOUD_CONFIG", os.path.join(BASE_DIR, "cloud_config.json"))

# Valeurs placeholder du template versionné : tant qu'elles ne sont pas remplacées
# par de vraies informations de compte, la persistance cloud reste désactivée
# plutôt que d'échouer bruyamment.
_PLACEHOLDER_MARKERS = {"votre_base", "votre_utilisateur", "votre_mot_de_passe", "VOTRE_CLE_ACCES", "VOTRE_CLE_SECRET"}


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_cloud_configured() -> bool:
    """True si cloud_config.json a été renseigné avec de vraies informations (pas le template)."""
    try:
        config = _load_config()
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    aws = config.get("aws_s3", {})
    supa = config.get("supabase", {})
    values = {aws.get("aws_access_key_id"), aws.get("aws_secret_access_key"), supa.get("user"), supa.get("password")}
    return bool(values) and not (values & _PLACEHOLDER_MARKERS)


@lru_cache(maxsize=1)
def _get_s3_client():
    import boto3
    config = _load_config()
    return boto3.client(
        "s3",
        aws_access_key_id=config["aws_s3"]["aws_access_key_id"],
        aws_secret_access_key=config["aws_s3"]["aws_secret_access_key"],
    )


def _get_supabase_connection():
    import psycopg2
    config = _load_config()
    supa = config["supabase"]
    return psycopg2.connect(
        dbname=supa["dbname"],
        user=supa["user"],
        password=supa["password"],
        host=supa["host"],
        port=supa["port"],
    )


def sauvegarder_donnees_brutes(data, bucket_name: str) -> bool:
    """Sauvegarde des données brutes dans S3. Nécessite cloud_config.json renseigné (voir is_cloud_configured())."""
    if not is_cloud_configured():
        logger.warning("Cloud non configuré (cloud_config.json contient encore le template) : sauvegarde S3 ignorée.")
        return False
    try:
        _get_s3_client().put_object(Bucket=bucket_name, Key="donnees_brutes.json", Body=json.dumps(data))
        logger.info("Données sauvegardées avec succès dans S3.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde dans S3: {e}")
        return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def inserer_donnees_arxiv(data) -> None:
    """Insertion des données dans Supabase. Nécessite cloud_config.json renseigné."""
    if not is_cloud_configured():
        logger.warning("Cloud non configuré : insertion Supabase ignorée.")
        return
    conn = _get_supabase_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO arxiv_articles (title, authors, abstract, pdf_url)
                VALUES (%s, %s, %s, %s)
                """,
                (data["title"], json.dumps(data["authors"]), data["abstract"], data["pdf_url"]),
            )
        conn.commit()
        logger.info("Données insérées avec succès dans Supabase.")
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion dans Supabase: {e}")
        raise
    finally:
        conn.close()


def main():
    if not is_cloud_configured():
        logger.error(
            "cloud_config.json contient encore les valeurs du template. "
            "Renseignez vos vraies informations AWS S3 / Supabase (ou FREEAI_CLOUD_CONFIG) avant d'exécuter ce script."
        )
        return

    exemple_donnees = {
        "title": "Titre de l'article ArXiv",
        "authors": ["Auteur 1", "Auteur 2"],
        "abstract": "Résumé de l'article",
        "pdf_url": "https://example.com/pdf.pdf",
    }
    config = _load_config()
    sauvegarder_donnees_brutes(exemple_donnees, config["aws_s3"]["bucket_name"])
    inserer_donnees_arxiv(exemple_donnees)


if __name__ == "__main__":
    main()