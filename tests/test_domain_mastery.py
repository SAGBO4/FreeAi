import pytest
from app.cognition.domain_mastery import DomainMasteryEngine
from app.memory.vector_memory import EphemeralVectorMemory


def test_domain_mastery_amm_calculation():
    engine = DomainMasteryEngine()
    res = engine.calculate_amm_swap(reserve_in=1000000, reserve_out=250, amount_in=5000)
    assert res["success"] is True
    assert res["amount_out"] > 1.2
    assert res["price_impact_pct"] > 0
    assert res["fee_paid"] == 15.0


def test_domain_mastery_indicators():
    engine = DomainMasteryEngine()
    prices = [100 + i * 2 for i in range(20)]
    ind = engine.calculate_technical_indicators(prices)
    assert ind["success"] is True
    assert ind["rsi_14"] > 70
    assert ind["rsi_condition"] == "SURACHAT (>70)"
    assert ind["bollinger"]["bandwidth_pct"] > 0


def test_domain_mastery_position_sizing():
    engine = DomainMasteryEngine()
    pos = engine.calculate_position_size(
        account_balance=10000,
        risk_pct=1.0,
        entry_price=100,
        stop_loss_price=95
    )
    assert pos["success"] is True
    assert pos["risk_amount"] == 100.0
    assert pos["units_to_trade"] == 20.0
    assert pos["total_position_value"] == 2000.0
    assert pos["effective_leverage"] == 0.2
    assert pos["status"] == "CONFORME"


def test_domain_mastery_autonomous_training():
    memory = EphemeralVectorMemory()
    engine = DomainMasteryEngine(vector_memory=memory)

    # Train blockchain
    bc_res = engine.run_autonomous_training_session("blockchain")
    assert bc_res["status"] == "completed"
    assert len(bc_res["insights_generated"]) >= 2

    # Train trading
    tr_res = engine.run_autonomous_training_session("trading")
    assert tr_res["status"] == "completed"
    assert len(tr_res["insights_generated"]) >= 2

    # Train mobile
    mob_res = engine.run_autonomous_training_session("mobile")
    assert mob_res["status"] == "completed"
    assert len(mob_res["insights_generated"]) >= 2

    # Verify vector memory assimilation
    assert len(memory.memories) >= 3
