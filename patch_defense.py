import re

with open("app/security/active_defense.py", "r") as f:
    content = f.read()

new_audit = """    async def audit_and_defend_request(
        self,
        source_ip: str,
        content: str,
        is_command: bool = False
    ) -> Tuple[bool, Optional[str]]:
        \"\"\"Audits an incoming request or command. If hostile, mounts active defense.
        Returns: (is_safe: bool, response_or_rejection: str)
        \"\"\"
        trusted_sources = ["master_or_gateway", "telegram_vault", "CLI", "127.0.0.1", "localhost"]
        is_trusted = source_ip in trusted_sources

        # 1. Check if IP is already banned
        if not is_trusted and self.is_ip_banned(source_ip):
            return False, "⛔ ACCÈS REFUSÉ : Votre adresse IP est sous embargo défensif."

        # 2. Check flood
        if not is_trusted and self.detect_flood(source_ip):
            incident = await self.defend_against_attack(
                source_ip=source_ip,
                attack_vector=AttackVector.DDOS_FLOOD,
                details=f"Inondation de requêtes détectée (> 20 req/s)."
            )
            return False, "🚨 FLOOD DÉTECTÉ : Connexion révoquée par le bouclier défensif."

        # 3. If command, audit through SovereignFortress
        if is_command and self.fortress:
            safe, reason = self.fortress.audit_command(content)
            if not safe:
                if is_trusted:
                    return False, f"🚨 VETO DÉFENSIF : {reason} (Ignoré car source maître, mais action annulée pour sécurité)"
                vector = AttackVector.REVERSE_SHELL if "Reverse Shell" in reason else AttackVector.TAMPERING
                await self.defend_against_attack(
                    source_ip=source_ip,
                    attack_vector=vector,
                    details=f"Tentative de commande hostile bloquée : '{content[:60]}...'"
                )
                return False, f"🚨 VETO DÉFENSIF : {reason}"

        # 4. If cognitive text, audit for prompt injections
        if self.fortress and not is_command:
            safe, reason = self.fortress.audit_prompt_injection(content)
            if not safe:
                if is_trusted:
                    return False, "🛡️ PARE-FEU COGNITIF : Requête annulée pour intégrité (Source maître)."
                await self.defend_against_attack(
                    source_ip=source_ip,
                    attack_vector=AttackVector.PROMPT_INJECTION,
                    details=f"Tentative d'injection de prompt interceptée : '{content[:60]}...'"
                )
                return False, "🛡️ PARE-FEU COGNITIF : Requête hostile neutralisée."

        return True, None"""

content = re.sub(r'    async def audit_and_defend_request.*?return True, None', new_audit, content, flags=re.DOTALL)

with open("app/security/active_defense.py", "w") as f:
    f.write(content)
