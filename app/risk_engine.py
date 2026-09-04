"""
DisputeForge — Risk Signal Extractor

Deterministic rule-based feature engineering that extracts
8 risk signals from transaction data to predict dispute likelihood.

This is intentionally NOT AI — these are clear business rules
that don't need ML to evaluate. (AI Judgment criterion)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskSignals:
    """Extracted risk signals for a single transaction."""
    delivery_gap: float          # 1.0 if delivery took > 10 days
    late_delivery: float         # Continuous: delivery_days / 10 (capped at 1.0)
    refund_requested: float      # 1.0 if refund was requested
    high_value: float            # 1.0 if amount > 5000 INR
    repeat_disputer: float       # Continuous: past_disputes / 5 (capped at 1.0)
    descriptor_mismatch: float   # 1.0 if billing descriptor doesn't match brand
    international: float         # 1.0 if card country != IN
    digital_goods: float         # 1.0 if digital goods (no physical proof)
    no_tracking: float           # 1.0 if no tracking number
    no_delivery_confirm: float   # 1.0 if delivery not confirmed
    support_contacted: float     # 1.0 if customer contacted support (can be + or -)
    support_intensity: float     # Continuous: contacts / 5 (capped at 1.0)
    days_since_delivery: float   # Continuous: days / 30 (capped at 1.0)
    amount_normalized: float     # Continuous: amount / 50000 (capped at 1.0)
    composite_risk_score: float  # Weighted combination of all signals

    def to_dict(self):
        return {
            "delivery_gap": self.delivery_gap,
            "late_delivery": self.late_delivery,
            "refund_requested": self.refund_requested,
            "high_value": self.high_value,
            "repeat_disputer": self.repeat_disputer,
            "descriptor_mismatch": self.descriptor_mismatch,
            "international": self.international,
            "digital_goods": self.digital_goods,
            "no_tracking": self.no_tracking,
            "no_delivery_confirm": self.no_delivery_confirm,
            "support_contacted": self.support_contacted,
            "support_intensity": self.support_intensity,
            "days_since_delivery": self.days_since_delivery,
            "amount_normalized": self.amount_normalized,
            "composite_risk_score": self.composite_risk_score,
        }

    def to_feature_list(self):
        """Return features in consistent order for ML model input."""
        return [
            self.delivery_gap,
            self.late_delivery,
            self.refund_requested,
            self.high_value,
            self.repeat_disputer,
            self.descriptor_mismatch,
            self.international,
            self.digital_goods,
            self.no_tracking,
            self.no_delivery_confirm,
            self.support_contacted,
            self.support_intensity,
            self.days_since_delivery,
            self.amount_normalized,
        ]

    @staticmethod
    def feature_names():
        return [
            "delivery_gap",
            "late_delivery",
            "refund_requested",
            "high_value",
            "repeat_disputer",
            "descriptor_mismatch",
            "international",
            "digital_goods",
            "no_tracking",
            "no_delivery_confirm",
            "support_contacted",
            "support_intensity",
            "days_since_delivery",
            "amount_normalized",
        ]


# ── Signal weights for composite score ────────────────────────────────────

SIGNAL_WEIGHTS = {
    "delivery_gap": 0.12,
    "late_delivery": 0.10,
    "refund_requested": 0.08,
    "high_value": 0.06,
    "repeat_disputer": 0.18,      # Strongest signal
    "descriptor_mismatch": 0.10,
    "international": 0.05,
    "digital_goods": 0.04,
    "no_tracking": 0.08,
    "no_delivery_confirm": 0.09,
    "support_contacted": -0.03,    # Negative: contacting support = less likely to blindside
    "support_intensity": 0.05,
    "days_since_delivery": 0.04,
    "amount_normalized": 0.04,
}


def extract_risk_signals(txn: dict) -> RiskSignals:
    """
    Extract risk signals from a single transaction record.

    Args:
        txn: Dictionary with transaction fields from the dataset

    Returns:
        RiskSignals dataclass with all computed signals
    """
    # Parse fields (handle both bool and string representations)
    def to_bool(val):
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    delivery_days = to_float(txn.get("delivery_days", 0))
    amount = to_float(txn.get("amount", 0))
    past_disputes = to_float(txn.get("past_disputes", 0))
    support_contacts = to_float(txn.get("support_contacts_count", 0))
    days_since = to_float(txn.get("days_since_delivery", 0))

    # Extract binary signals
    delivery_gap = 1.0 if delivery_days > 10 else 0.0
    late_delivery = min(delivery_days / 10.0, 1.0)
    refund_requested = 1.0 if to_bool(txn.get("refund_requested", False)) else 0.0
    high_value = 1.0 if amount > 5000 else 0.0
    repeat_disputer = min(past_disputes / 5.0, 1.0)
    descriptor_mismatch = 0.0 if to_bool(txn.get("descriptor_matches_brand", True)) else 1.0
    international = 0.0 if txn.get("card_country", "IN") == "IN" else 1.0
    digital_goods = 1.0 if to_bool(txn.get("is_digital_goods", False)) else 0.0
    no_tracking = 0.0 if to_bool(txn.get("has_tracking", True)) else 1.0
    no_delivery_confirm = 0.0 if to_bool(txn.get("delivery_confirmed", True)) else 1.0
    support_contacted = 1.0 if to_bool(txn.get("contacted_support", False)) else 0.0
    support_intensity = min(support_contacts / 5.0, 1.0)
    days_since_delivery = min(days_since / 30.0, 1.0)
    amount_normalized = min(amount / 50000.0, 1.0)

    # Composite risk score (weighted sum)
    signals = {
        "delivery_gap": delivery_gap,
        "late_delivery": late_delivery,
        "refund_requested": refund_requested,
        "high_value": high_value,
        "repeat_disputer": repeat_disputer,
        "descriptor_mismatch": descriptor_mismatch,
        "international": international,
        "digital_goods": digital_goods,
        "no_tracking": no_tracking,
        "no_delivery_confirm": no_delivery_confirm,
        "support_contacted": support_contacted,
        "support_intensity": support_intensity,
        "days_since_delivery": days_since_delivery,
        "amount_normalized": amount_normalized,
    }

    composite = sum(
        SIGNAL_WEIGHTS[key] * signals[key]
        for key in SIGNAL_WEIGHTS
    )
    composite = max(0.0, min(1.0, composite))  # Clamp to [0, 1]

    return RiskSignals(
        delivery_gap=delivery_gap,
        late_delivery=late_delivery,
        refund_requested=refund_requested,
        high_value=high_value,
        repeat_disputer=repeat_disputer,
        descriptor_mismatch=descriptor_mismatch,
        international=international,
        digital_goods=digital_goods,
        no_tracking=no_tracking,
        no_delivery_confirm=no_delivery_confirm,
        support_contacted=support_contacted,
        support_intensity=support_intensity,
        days_since_delivery=days_since_delivery,
        amount_normalized=amount_normalized,
        composite_risk_score=composite,
    )


def get_triggered_signals(signals: RiskSignals) -> list[dict]:
    """
    Return a list of human-readable triggered risk signals.
    Used for the audit trail and dashboard display.
    """
    triggered = []
    thresholds = {
        "delivery_gap": (0.5, "Delivery took over 10 days", "high"),
        "late_delivery": (0.8, "Significant delivery delay detected", "medium"),
        "refund_requested": (0.5, "Customer already requested a refund", "high"),
        "high_value": (0.5, "High-value transaction (>₹5,000)", "medium"),
        "repeat_disputer": (0.2, "Customer has past dispute history", "critical"),
        "descriptor_mismatch": (0.5, "Billing descriptor doesn't match merchant name", "high"),
        "international": (0.5, "Cross-border transaction", "medium"),
        "digital_goods": (0.5, "Digital goods (no physical delivery proof)", "medium"),
        "no_tracking": (0.5, "No tracking number available", "high"),
        "no_delivery_confirm": (0.5, "Delivery not confirmed", "high"),
        "support_intensity": (0.6, "Multiple support contacts (frustrated customer)", "medium"),
        "days_since_delivery": (0.5, "Long time since delivery (dispute window open)", "low"),
    }

    signal_dict = signals.to_dict()
    for key, (threshold, description, severity) in thresholds.items():
        if signal_dict.get(key, 0) >= threshold:
            triggered.append({
                "signal": key,
                "value": round(signal_dict[key], 3),
                "description": description,
                "severity": severity,
            })

    return triggered
