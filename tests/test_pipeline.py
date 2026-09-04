"""
DisputeForge — Pipeline Integration Tests

Tests the full pipeline: data → risk signals → prediction → evidence → deflection
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.risk_engine import extract_risk_signals, get_triggered_signals
from app.predictor import DisputePredictor
from app.evidence import EvidenceOrchestrator
from app.deflector import DeflectionEngine


def test_risk_signal_extraction():
    """Test that risk signals are extracted correctly from transaction data."""
    print("🧪 Test: Risk Signal Extraction")

    # High-risk transaction
    txn = {
        "payment_id": "pay_test_001",
        "amount": 8000,
        "delivery_days": 15,
        "delivery_confirmed": False,
        "has_tracking": False,
        "descriptor_matches_brand": False,
        "card_country": "US",
        "is_digital_goods": False,
        "past_disputes": 3,
        "contacted_support": False,
        "support_contacts_count": 0,
        "refund_requested": True,
        "refund_status": "pending",
        "days_since_delivery": 20,
    }

    signals = extract_risk_signals(txn)

    assert signals.high_value == 1.0, f"Expected high_value=1.0, got {signals.high_value}"
    assert signals.delivery_gap == 1.0, f"Expected delivery_gap=1.0, got {signals.delivery_gap}"
    assert signals.no_tracking == 1.0, f"Expected no_tracking=1.0, got {signals.no_tracking}"
    assert signals.descriptor_mismatch == 1.0, f"Expected descriptor_mismatch=1.0, got {signals.descriptor_mismatch}"
    assert signals.international == 1.0, f"Expected international=1.0, got {signals.international}"
    assert signals.refund_requested == 1.0, f"Expected refund_requested=1.0, got {signals.refund_requested}"
    assert signals.repeat_disputer > 0, f"Expected repeat_disputer>0, got {signals.repeat_disputer}"
    assert signals.composite_risk_score > 0.3, f"Expected composite>0.3, got {signals.composite_risk_score}"

    triggered = get_triggered_signals(signals)
    assert len(triggered) > 3, f"Expected >3 triggered signals, got {len(triggered)}"

    print(f"   ✅ Signals extracted: composite_risk_score={signals.composite_risk_score:.3f}")
    print(f"   ✅ Triggered signals: {len(triggered)}")

    # Low-risk transaction
    txn_low = {
        "payment_id": "pay_test_002",
        "amount": 500,
        "delivery_days": 3,
        "delivery_confirmed": True,
        "has_tracking": True,
        "descriptor_matches_brand": True,
        "card_country": "IN",
        "is_digital_goods": False,
        "past_disputes": 0,
        "contacted_support": False,
        "support_contacts_count": 0,
        "refund_requested": False,
        "refund_status": "none",
        "days_since_delivery": 5,
    }

    signals_low = extract_risk_signals(txn_low)
    assert signals_low.composite_risk_score < signals.composite_risk_score, \
        "Low-risk should have lower score than high-risk"

    print(f"   ✅ Low-risk score: {signals_low.composite_risk_score:.3f} < {signals.composite_risk_score:.3f}")
    print()


def test_predictor():
    """Test the dispute predictor (with or without trained model)."""
    print("🧪 Test: Dispute Predictor")

    predictor = DisputePredictor()

    txn = {
        "amount": 12000,
        "delivery_days": 20,
        "delivery_confirmed": False,
        "has_tracking": False,
        "descriptor_matches_brand": False,
        "card_country": "IN",
        "is_digital_goods": False,
        "past_disputes": 4,
        "contacted_support": False,
        "support_contacts_count": 0,
        "refund_requested": True,
        "refund_status": "denied",
        "days_since_delivery": 25,
    }

    signals = extract_risk_signals(txn)
    prediction = predictor.predict(signals)

    assert "dispute_probability" in prediction
    assert "risk_level" in prediction
    assert "model_used" in prediction
    assert 0 <= prediction["dispute_probability"] <= 1

    print(f"   ✅ Prediction: prob={prediction['dispute_probability']:.3f}, "
          f"level={prediction['risk_level']}, model={prediction['model_used']}")
    print()


def test_evidence_orchestrator():
    """Test evidence package generation."""
    print("🧪 Test: Evidence Orchestrator")

    engine = EvidenceOrchestrator()

    txn = {
        "payment_id": "pay_test_evidence",
        "order_id": "order_test_123",
        "amount": 5500,
        "txn_date": "2026-08-15",
        "merchant_name": "TestMart Electronics",
        "billing_descriptor": "TESTMART*ELEC",
        "card_network": "Visa",
        "delivery_confirmed": True,
        "has_tracking": True,
        "tracking_number": "BlueDart-123456789",
        "delivery_date": "2026-08-18",
        "contacted_support": False,
        "past_disputes": 1,
        "refund_status": "none",
    }

    prediction = {
        "dispute_probability": 0.82,
        "risk_level": "critical",
        "predicted_dispute_type": "friendly_fraud",
    }

    package = engine.generate_evidence_package(txn, prediction, [])

    assert "narrative" in package
    assert "evidence_checklist" in package
    assert "evidence_strength" in package
    assert len(package["narrative"]) > 50, "Narrative too short"
    assert package["evidence_strength"]["score"] > 0

    print(f"   ✅ Evidence package generated: strength={package['evidence_strength']['rating']}")
    print(f"   ✅ Narrative length: {len(package['narrative'])} chars")
    print(f"   ✅ Generation method: {package['generation_method']}")
    print()


def test_deflection_engine():
    """Test deflection message generation."""
    print("🧪 Test: Deflection Engine")

    engine = DeflectionEngine()

    txn = {
        "payment_id": "pay_test_deflect",
        "order_id": "order_test_456",
        "amount": 3200,
        "merchant_name": "QuickMart Electronics",
        "billing_descriptor": "QKMART*ELECTRONICS",
        "delivery_date": "2026-08-20",
        "delivery_confirmed": True,
        "tracking_number": "Delhivery-987654321",
        "delivery_days": 5,
    }

    prediction = {
        "dispute_probability": 0.75,
        "risk_level": "high",
        "predicted_dispute_type": "friendly_fraud",
    }

    deflection = engine.generate_deflection(txn, prediction)

    assert "message" in deflection
    assert "channel" in deflection
    assert "timing" in deflection
    assert len(deflection["message"]) > 20
    assert deflection["timing"]["urgency"] in ("immediate", "high", "medium", "low")

    print(f"   ✅ Deflection generated: channel={deflection['channel']}")
    print(f"   ✅ Urgency: {deflection['timing']['urgency']}")
    print(f"   ✅ Message length: {len(deflection['message'])} chars")
    print()


def test_full_pipeline():
    """Test the complete pipeline end-to-end."""
    print("🧪 Test: Full Pipeline (End-to-End)")

    predictor = DisputePredictor()
    evidence_engine = EvidenceOrchestrator()
    deflection_engine = DeflectionEngine()

    # Simulate a batch of 5 transactions
    transactions = [
        {"payment_id": "pay_clean", "amount": 800, "delivery_days": 3, "delivery_confirmed": True,
         "has_tracking": True, "descriptor_matches_brand": True, "card_country": "IN",
         "is_digital_goods": False, "past_disputes": 0, "contacted_support": False,
         "support_contacts_count": 0, "refund_requested": False, "refund_status": "none",
         "days_since_delivery": 5, "merchant_name": "TestMart", "card_network": "Visa",
         "txn_date": "2026-08-10", "delivery_date": "2026-08-13", "tracking_number": "BD-111"},

        {"payment_id": "pay_risky", "amount": 15000, "delivery_days": 18, "delivery_confirmed": False,
         "has_tracking": False, "descriptor_matches_brand": False, "card_country": "US",
         "is_digital_goods": False, "past_disputes": 5, "contacted_support": False,
         "support_contacts_count": 0, "refund_requested": True, "refund_status": "denied",
         "days_since_delivery": 30, "merchant_name": "RiskyShop", "card_network": "Visa",
         "billing_descriptor": "RZP*RISKY", "txn_date": "2026-08-01", "delivery_date": "2026-08-19"},
    ]

    results = []
    for txn in transactions:
        signals = extract_risk_signals(txn)
        prediction = predictor.predict(signals)
        triggered = get_triggered_signals(signals)

        result = {
            "payment_id": txn["payment_id"],
            "risk_score": signals.composite_risk_score,
            "dispute_prob": prediction["dispute_probability"],
            "risk_level": prediction["risk_level"],
            "signals_triggered": len(triggered),
        }

        if prediction["dispute_probability"] >= 0.5:
            deflection = deflection_engine.generate_deflection(txn, prediction)
            result["deflection"] = True

        if prediction["dispute_probability"] >= 0.6:
            evidence = evidence_engine.generate_evidence_package(txn, prediction, triggered)
            result["evidence"] = True

        results.append(result)

    clean = results[0]
    risky = results[1]

    assert risky["dispute_prob"] > clean["dispute_prob"], "Risky should have higher prob"
    assert risky["signals_triggered"] > clean["signals_triggered"], "Risky should have more signals"

    print(f"   ✅ Clean transaction: prob={clean['dispute_prob']:.3f}, level={clean['risk_level']}")
    print(f"   ✅ Risky transaction: prob={risky['dispute_prob']:.3f}, level={risky['risk_level']}")
    print(f"   ✅ Pipeline correctly differentiates risk levels")
    print()


if __name__ == "__main__":
    print("\n🛡️  DisputeForge — Pipeline Tests")
    print("=" * 50)

    try:
        test_risk_signal_extraction()
        test_predictor()
        test_evidence_orchestrator()
        test_deflection_engine()
        test_full_pipeline()

        print("=" * 50)
        print("✅ All tests passed!")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
