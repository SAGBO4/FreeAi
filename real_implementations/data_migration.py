import json
import boto3
import psycopg2
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import logging

# Configuration
config = json.load(open('/home/lesaint/Rendue/FreeAi/real_implementations/cloud_config.json'))

# Configuration AWS S3
s3 = boto3.client('s3',
                  aws_access_key_id=config['aws_s3']['aws_access_key_id'],
                  aws_secret_access_key=config['aws_s3']['aws_secret_access_key'])

# Configuration Supabase
supabase_conn = psycopg2.connect(
    dbname=config['supabase']['dbname'],
    user=config['supabase']['user'],
    password=config['supabase']['password'],
    host=config['supabase']['host'],
    port=config['supabase']['port']
)

# Configuration Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sauvegarde des données brutes dans S3
def sauvegarder_donnees_brutes(data, bucket_name):
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key="donnees_brutes.json",
            Body=json.dumps(data)
        )
        logger.info("Données sauvegardées avec succès dans S3.")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde dans S3: {e}")

# Insertion des données dans Supabase
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def inserer_donnees_arxiv(data):
    try:
        with supabase_conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO arxiv_articles (title, authors, abstract, pdf_url)
                VALUES (%s, %s, %s, %s)
                """,
                (data['title'], json.dumps(data['authors']), data['abstract'], data['pdf_url'])
            )
        supabase_conn.commit()
        logger.info("Données insérées avec succès dans Supabase.")
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion dans Supabase: {e}")
        raise

# Exemple d'utilisation
def main():
    exemple_donnees = {
        "title": "Titre de l'article ArXiv",
        "authors": ["Auteur 1", "Auteur 2"],
        "abstract": "Résumé de l'article",
        "pdf_url": "https://example.com/pdf.pdf"
    }
    sauvegarder_donnees_brutes(exemple_donnees, config['aws_s3']['bucket_name'])
    inserer_donnees_arxiv(exemple_donnees)

if __name__ == "__main__":
    main()