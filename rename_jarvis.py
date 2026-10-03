import os
import glob
import re

replacements = {
    r"<\|genese\|>": "<|jarvis|>",
    r"genese-s0-v0001": "jarvis-s0-v0001",
    r"Genèse": "Jarvis",
    r"Genese": "Jarvis",
    r"GENÈSE": "JARVIS",
    r"GENESE": "JARVIS",
    r"/genese": "/jarvis",
    r"genese_runtime": "jarvis_runtime",
    r"genese_ans": "jarvis_ans",
    r"handle_genese_command": "handle_jarvis_command",
    r"TokenizerGenese": "TokenizerJarvis",
    r"GeneseModele": "JarvisModele",
    r"GeneseCoreRuntime": "JarvisCoreRuntime",
    r"BlocGenese": "BlocJarvis"
}

files_to_check = glob.glob("app/llm/genese/**/*.py", recursive=True)
files_to_check += ["app/llm/engine.py", "cli.py", "tests/test_genese_bootstrap.py"]

for fpath in files_to_check:
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        orig_content = content
        
        for k, v in replacements.items():
            content = re.sub(k, v, content)
            
        if content != orig_content:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Patched: {fpath}")

# Add nom="jarvis-s0-v0001" to ADNModele
adn_path = "app/llm/genese/adn.py"
with open(adn_path, "r", encoding="utf-8") as f:
    adn_content = f.read()

if "nom: str" not in adn_content:
    adn_content = adn_content.replace(
        "    dense: bool = True",
        "    dense: bool = True\n    nom: str = \"jarvis-s0-v0001\""
    )
    with open(adn_path, "w", encoding="utf-8") as f:
        f.write(adn_content)
    print("Added nom to ADNModele")

