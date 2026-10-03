import argparse
import asyncio
from .distillateur import DistillateurBenchmark

async def main():
    parser = argparse.ArgumentParser(description="Bootstrap Jarvis via Distillation")
    parser.add_argument("--categorie", type=str, help="Catégorie spécifique à distiller")
    parser.add_argument("--all", action="store_true", help="Toutes les catégories")
    parser.add_argument("--n", type=int, default=10, help="Nombre de prompts")
    parser.add_argument("--rapport", action="store_true", help="Affiche juste le rapport (non implémenté)")
    args = parser.parse_args()

    distillateur = DistillateurBenchmark(index_memoire=None)
    
    cats = None
    if args.categorie:
        cats = [args.categorie]
    elif not args.all:
        cats = []
        
    if cats is not None or args.all:
        print(f"Lancement de la session de bootstrap (n={args.n})...")
        stats = await distillateur.run_benchmark_session(n_prompts_par_categorie=args.n, categories=cats)
        print("Résultats de la session :")
        print(stats)

if __name__ == "__main__":
    asyncio.run(main())
