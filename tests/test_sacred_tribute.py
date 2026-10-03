"""Unit tests for Sacred Tribute Vault & Birthday Crypto Gift Protocol (Michael SAGBO)."""

import pytest
from datetime import date
from app.cognition.sacred_tribute import SacredTributeVault
from app.cognition.persona import ConversationalPersona
from app.memory.vector_memory import EphemeralVectorMemory


class TestSacredTribute:
    def setup_method(self):
        self.memory = EphemeralVectorMemory()
        self.tribute = SacredTributeVault(vector_memory=self.memory)

    def test_immutable_profile_data(self):
        assert self.tribute.MASTER_NAME == "Michael SAGBO"
        assert self.tribute.BIRTH_YEAR == 2002
        assert self.tribute.BIRTH_MONTH == 2
        assert self.tribute.BIRTH_DAY == 5
        assert self.tribute.TARGET_GIFT_AMOUNT_USD == 500.0

    def test_is_birthday_detection(self):
        # 5th of February must return True
        bday = date(2027, 2, 5)
        assert self.tribute.is_birthday(bday) is True

        # Other dates must return False
        other_day = date(2027, 2, 6)
        assert self.tribute.is_birthday(other_day) is False
        other_month = date(2027, 10, 4)
        assert self.tribute.is_birthday(other_month) is False

    def test_days_until_birthday(self):
        # Day before
        day_before = date(2027, 2, 4)
        assert self.tribute.get_days_until_birthday(day_before) == 1

        # On the day
        bday = date(2027, 2, 5)
        assert self.tribute.get_days_until_birthday(bday) == 0

        # Day after
        day_after = date(2027, 2, 6)
        assert self.tribute.get_days_until_birthday(day_after) == 364

    def test_age_calculation(self):
        # Birthday in 2026
        d_2026 = date(2026, 2, 5)
        assert self.tribute.get_age(d_2026) == 24

        # Before birthday in 2026
        d_before = date(2026, 1, 15)
        assert self.tribute.get_age(d_before) == 23

    def test_12_word_seed_generation(self):
        words = self.tribute.generate_12_word_seed()
        assert isinstance(words, list)
        assert len(words) == 12
        for w in words:
            assert isinstance(w, str)
            assert len(w) > 0

    def test_crypto_gift_payload(self):
        gift = self.tribute.generate_crypto_gift(target_usd=500.0)
        assert gift["success"] is True
        assert gift["recipient"] == "Michael SAGBO"
        assert gift["target_amount_usd"] == 500.0
        assert len(gift["mnemonic_words"]) == 12
        assert len(gift["mnemonic_sentence"].split()) == 12
        assert "500$" in gift["message"]
        assert "12 mots" in gift["message"]

    def test_conversational_triggers(self):
        # Trigger on 'anniversaire'
        res1 = self.tribute.check_conversational_trigger("C'est quand mon anniversaire ?")
        assert res1 is not None
        assert res1["triggered"] is True

        # Trigger on '5 février'
        res2 = self.tribute.check_conversational_trigger("N'oublie pas le 5 février")
        assert res2 is not None
        assert res2["triggered"] is True

        # Trigger on '12 mots'
        res3 = self.tribute.check_conversational_trigger("Envoie-moi mes 12 mots")
        assert res3 is not None
        assert res3["triggered"] is True

        # Non-trigger
        res_none = self.tribute.check_conversational_trigger("Quel temps fait-il aujourd'hui ?")
        assert res_none is None

    def test_persona_birthday_integration(self):
        import asyncio
        persona = ConversationalPersona(vector_memory=self.memory)
        res = asyncio.run(persona.chat("Souviens-toi de mon anniversaire et envoie-moi mes 12 mots"))
        assert res["success"] is True
        assert res.get("conversational") is True
        assert "5 Février 2002" in res["output"] or "5 février" in res["output"].lower()
        # Verify 12 words are present in the response
        assert "12 mots" in res["output"] or "mots" in res["output"]

    def test_challenge_overview(self):
        ov = self.tribute.get_challenge_overview()
        assert ov["target_amount_usd"] == 500.0
        assert len(ov["pillars"]) >= 4
        assert "USDC" in ov["acceptable_currencies"]
        assert ov["status"] == "CHALLENGE_ACCEPTED_AND_ENGAGED"
