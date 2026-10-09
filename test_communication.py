#!/usr/bin/env python3

import requests
import time
import sys

# URL du coordinateur
COORDINATOR_URL = "http://localhost:8000"
WORKER_URLS = ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003", "http://localhost:8004"]


def test_coordinator():
    """Tester si le coordinateur répond."""
    try:
        response = requests.get(f"{COORDINATOR_URL}/health")
        if response.status_code == 200:
            print("✅ Coordinateur est opérationnel.")
            return True
        else:
            print(f"❌ Coordinateur ne répond pas correctement: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur lors de la connexion au coordinateur: {e}")
        return False


def test_workers():
    """Tester si les workers répondent."""
    for url in WORKER_URLS:
        try:
            response = requests.get(f"{url}/health")
            if response.status_code == 200:
                print(f"✅ Worker sur {url} est opérationnel.")
            else:
                print(f"❌ Worker sur {url} ne répond pas correctement: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur lors de la connexion au worker {url}: {e}")


def main():
    print("Test de la communication entre les conteneurs...")

    # Attendre que les conteneurs soient prêts
    time.sleep(5)

    # Tester le coordinateur
    coordinator_ok = test_coordinator()

    # Tester les workers
    test_workers()

    if coordinator_ok:
        print("\n🎉 Tous les tests sont terminés.")
    else:
        print("\n❌ Certains services ne sont pas opérationnels.")
        sys.exit(1)


if __name__ == "__main__":
    main()