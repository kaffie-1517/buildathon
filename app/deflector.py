"""
DisputeForge — Pre-Dispute Deflection Engine

Generates proactive outreach messages to resolve issues BEFORE
the customer files a chargeback. This is the core differentiator —
Razorpay's Dispute Responder is reactive, this is preventive.
"""

from datetime import datetime


# ── Deflection Templates by Dispute Type ──────────────────────────────────

DEFLECTION_TEMPLATES = {
    "friendly_fraud": {
        "channel": "email",
        "subject": "Quick check on your recent order",
        "tone": "warm",
        "templates": [
            (
                "Hi there! We noticed your order #{order_id} (₹{amount}) from "
                "{merchant} was delivered on {delivery_date}. We hope everything "
                "arrived in good condition! If you have any concerns about your "
                "purchase, our support team is here to help — just reply to this "
                "message. We'd love to resolve anything before it becomes a hassle."
            ),
            (
                "Hello! Just following up on your recent purchase of ₹{amount} from "
                "{merchant}. Your order #{order_id} shows as delivered. If the item "
                "isn't what you expected, we have a hassle-free return process — "
                "no need to contact your bank. Reply here and we'll sort it out "
                "within 24 hours."
            ),
        ],
    },
    "late_delivery": {
        "channel": "sms_and_email",
        "subject": "Update on your delayed order",
        "tone": "apologetic",
        "templates": [
            (
                "We sincerely apologize for the delay on your order #{order_id}. "
                "We understand waiting {delivery_days} days is frustrating. Your "
                "package is now {delivery_status} via {tracking}. If you'd like a "
                "refund or replacement instead, reply here — we'll process it "
                "immediately, no questions asked."
            ),
            (
                "Hi! We know your order #{order_id} (₹{amount}) took longer than "
                "expected. We're sorry about that. As a goodwill gesture, we'd like "
                "to offer you a {discount}% discount on your next purchase. If you'd "
                "prefer a refund, just let us know — we'll handle it within 48 hours."
            ),
        ],
    },
    "descriptor_confusion": {
        "channel": "email",
        "subject": "About the charge from {descriptor} on your statement",
        "tone": "clarifying",
        "templates": [
            (
                "Hi! You may have noticed a charge of ₹{amount} from "
                "\"{descriptor}\" on your bank statement. This is your purchase "
                "from {merchant} on {txn_date}. The name looks different because "
                "\"{descriptor}\" is our registered billing name. If you don't "
                "recognize this purchase, please contact us at support before "
                "reaching out to your bank — we can resolve this much faster!"
            ),
        ],
    },
    "serial_disputer": {
        "channel": "email",
        "subject": "Regarding your recent orders",
        "tone": "firm_but_fair",
        "templates": [
            (
                "Hi! We've noticed some concerns with your recent orders from "
                "{merchant}. We value your business and want to ensure you're "
                "satisfied. If there are ongoing issues with your purchases, "
                "our dedicated support team can help resolve them directly. "
                "Please reach out to us first — we can often provide faster "
                "resolution than the dispute process."
            ),
        ],
    },
    "cross_border": {
        "channel": "email",
        "subject": "Your international purchase confirmation",
        "tone": "reassuring",
        "templates": [
            (
                "Hi! Thank you for your international purchase of ₹{amount} from "
                "{merchant}. Your order #{order_id} is being processed. Please note "
                "that international deliveries may take {delivery_days}-{delivery_days_max} "
                "business days. You can track your package here: {tracking}. "
                "If you have any concerns, contact us directly — we're here to help!"
            ),
        ],
    },
    "legitimate": {
        "channel": "email",
        "subject": "We're working on your concern",
        "tone": "empathetic",
        "templates": [
            (
                "Hi! We see you've contacted our support team about order "
                "#{order_id}. We're actively working on resolving your concern. "
                "Your refund/replacement request is being processed and you should "
                "hear back within {resolution_hours} hours. We appreciate your "
                "patience — please allow us to resolve this directly."
            ),
        ],
    },
}


class DeflectionEngine:
    """
    Generates proactive outreach messages to prevent chargebacks.
    Uses templates with transaction-specific personalization.
    """

    def generate_deflection(self, txn: dict, prediction: dict) -> dict:
        """
        Generate a deflection message for a high-risk transaction.

        Args:
            txn: Transaction data
            prediction: Model prediction result

        Returns:
            Deflection action dict with message, channel, timing
        """
        dispute_type = prediction.get("predicted_dispute_type", "friendly_fraud")
        template_config = DEFLECTION_TEMPLATES.get(
            dispute_type, DEFLECTION_TEMPLATES["friendly_fraud"]
        )

        # Select template (round-robin based on payment_id hash)
        templates = template_config["templates"]
        idx = hash(txn.get("payment_id", "")) % len(templates)
        template = templates[idx]

        # Fill template with transaction data
        message = self._fill_template(template, txn)
        subject = self._fill_template(template_config.get("subject", ""), txn)

        # Determine timing
        timing = self._determine_timing(txn, prediction)

        return {
            "payment_id": txn.get("payment_id"),
            "action_type": "proactive_outreach",
            "channel": template_config["channel"],
            "subject": subject,
            "message": message,
            "tone": template_config["tone"],
            "timing": timing,
            "dispute_type": dispute_type,
            "dispute_probability": prediction.get("dispute_probability", 0),
            "generated_at": datetime.now().isoformat(),
            "status": "pending_send",
        }

    def _fill_template(self, template: str, txn: dict) -> str:
        """Fill template placeholders with transaction data."""
        replacements = {
            "{order_id}": str(txn.get("order_id", "N/A")),
            "{amount}": str(txn.get("amount", "N/A")),
            "{merchant}": str(txn.get("merchant_name", "the merchant")),
            "{delivery_date}": str(txn.get("delivery_date", "recently")),
            "{delivery_days}": str(txn.get("delivery_days", "several")),
            "{delivery_days_max}": str(int(txn.get("delivery_days", 7)) + 5),
            "{delivery_status}": "delivered" if txn.get("delivery_confirmed") in (True, "True", "true") else "in transit",
            "{tracking}": str(txn.get("tracking_number", "N/A")),
            "{txn_date}": str(txn.get("txn_date", "recently")),
            "{descriptor}": str(txn.get("billing_descriptor", "N/A")),
            "{discount}": "15",
            "{resolution_hours}": "48",
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        return result

    def _determine_timing(self, txn: dict, prediction: dict) -> dict:
        """Determine when to send the deflection message."""
        prob = prediction.get("dispute_probability", 0)
        dispute_type = prediction.get("predicted_dispute_type", "")

        if prob >= 0.85:
            urgency = "immediate"
            send_within = "1 hour"
        elif prob >= 0.7:
            urgency = "high"
            send_within = "4 hours"
        elif prob >= 0.5:
            urgency = "medium"
            send_within = "24 hours"
        else:
            urgency = "low"
            send_within = "48 hours"

        # Late delivery gets faster outreach
        if dispute_type == "late_delivery":
            urgency = "immediate"
            send_within = "1 hour"

        return {
            "urgency": urgency,
            "send_within": send_within,
            "best_channel": "sms" if urgency == "immediate" else "email",
        }

    def generate_batch_deflections(self, transactions: list[dict], predictions: list[dict], threshold: float = 0.5) -> list[dict]:
        """Generate deflection messages for all high-risk transactions in a batch."""
        deflections = []
        for txn, pred in zip(transactions, predictions):
            if pred.get("dispute_probability", 0) >= threshold:
                deflection = self.generate_deflection(txn, pred)
                deflections.append(deflection)
        return deflections
