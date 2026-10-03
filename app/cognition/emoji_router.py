def classify_response_emoji(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ["code", "bug", "python", "script", "technique"]):
        return "💻"
    elif any(k in text_lower for k in ["freeai", "jarvis", "je suis", "intelligence"]):
        return "🤖"
    elif any(k in text_lower for k in ["alerte", "urgent", "attention", "erreur", "fail"]):
        return "🚨"
    elif any(k in text_lower for k in ["innovation", "appris", "compris", "idée"]):
        return "🧠"
    elif any(k in text_lower for k in ["succès", "accompli", "terminé", "réussi", "ok"]):
        return "✅"
    return "💬"
