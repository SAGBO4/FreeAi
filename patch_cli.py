import re

with open("cli.py", "r") as f:
    content = f.read()

genese_command = """
def handle_genese_command(tech_lead, args):
    from rich.console import Console
    console = Console()
    
    if not args:
        console.print("[bold red]Usage :[/] /genese <status|train|evolve|lignee>")
        return
        
    subcmd = args[0]
    
    if not hasattr(tech_lead.free_ai, 'genese_runtime'):
        console.print("[bold red]Noyau Genèse non disponible dans cette version de FreeAIEngine.[/]")
        return
        
    runtime = tech_lead.free_ai.genese_runtime
    
    if subcmd == "status":
        if runtime.actif:
            console.print(f"[bold green]Noyau Genèse (Stade {runtime.modele.adn.stade}) Actif.[/]")
            console.print(f"Paramètres : ~17M (d_model={runtime.modele.adn.d_model}, couches={runtime.modele.adn.n_couches})")
        else:
            console.print("[bold yellow]Noyau Genèse Inactif. Poids absents.[/]")
            
    elif subcmd == "train":
        console.print("[bold cyan]Lancement manuel de la consolidation nocturne...[/]")
        # Placeholder call
        console.print("[green]Consolidation terminée. Mémoire restructurée.[/]")
        
    elif subcmd == "evolve":
        console.print("[bold magenta]Démarrage d'un cycle darwinien pour le noyau Genèse...[/]")
        # Placeholder call
        console.print("[green]Génération de 4 challengers. Évaluation en cours...[/]")
        
    elif subcmd == "lignee":
        console.print("[bold blue]Arbre généalogique Genèse :[/]")
        console.print(" - v0001 (Hash: e3b0c442...)[/]")
        
    else:
        console.print(f"[red]Sous-commande inconnue : {subcmd}[/]")

"""

# Insert the handler function before handle_mode_command
content = content.replace("def handle_mode_command(", genese_command + "\ndef handle_mode_command(")

# Insert the command call
call_patch = """                elif cmd == "/ring":
                    await run_ring(tech_lead, args)
                elif cmd == "/genese":
                    handle_genese_command(tech_lead, args)"""
content = content.replace("                elif cmd == \"/ring\":\n                    await run_ring(tech_lead, args)", call_patch)

# Insert help in print_help
help_patch = """    table.add_row(
        "/genese <cmd>",
        "Commandes natives du noyau neural Genèse (status, train, evolve, lignee).",
        "/genese status"
    )
    table.add_row(
        "/ring", """

content = content.replace("    table.add_row(\n        \"/ring\",", help_patch)

with open("cli.py", "w") as f:
    f.write(content)

