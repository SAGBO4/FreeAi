import re

with open("app/memory/telegram_vault.py", "r") as f:
    content = f.read()

# 1. Fix is_master_user
new_is_master = """    def is_master_user(self, user_id: str, username: Optional[str] = None) -> bool:
        \"\"\"Verifies if the sender is Michael SAGBO (by user_id, chat_id or known handles).\"\"\"
        uid = str(user_id).strip()
        if uid in (str(self.master_user_id), str(self.chat_id), "6149977795"):
            return True
        if username:
            u_clean = username.lower().lstrip("@")
            if u_clean in ("speedylesaint", "sagbo4"):
                return True
        return False"""
content = re.sub(r'    def is_master_user.*?return False', new_is_master, content, flags=re.DOTALL)

# 2. Fix is_group logic and intrusion alert
old_is_group = 'is_group = msg.get("chat", {}).get("type") in ["group", "supergroup"]'
new_is_group = 'is_group = msg.get("chat", {}).get("type") in ["group", "supergroup"] or str(sender_chat_id).startswith("-")'
content = content.replace(old_is_group, new_is_group)

# 3. Ensure target_chat_id is properly used for /setup_hq and messages
# Wait, let's just make sure is_group protects negative chat_ids
# And make sure admin commands in group don't crash if is_master is somehow false (but it won't be false anymore)

with open("app/memory/telegram_vault.py", "w") as f:
    f.write(content)
