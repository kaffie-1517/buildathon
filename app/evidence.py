"""
DisputeForge — Evidence Orchestrator

LLM-powered evidence package generator that creates reason-code-specific
evidence narratives. This is where AI IS appropriate — crafting persuasive,
contextual arguments requires reasoning, not rules.
"""

import os
import json
from datetime import datetime

# Try importing Gemini
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from dotenv import load_dotenv
from app.ai_engine import AIEngine

load_dotenv()


# ── Evidence Templates (Reason-Code-Specific) ────────────────────────────

EVIDENCE_TEMPLATES = {
    "friendly_fraud": {
        "title": "Friendly Fraud — Product Received But Disputed",
        "required_evidence": [
            "Delivery confirmation with tracking",
            "Proof of delivery (signature/photo)",
            "Customer communication history",
            "Product description accuracy",
            "Refund/return policy visibility",
        ],
        "key_argument": "The cardholder received the product as described and confirmed delivery exists.",
    },
    "legitimate": {
        "title": "Legitimate Dispute — Acknowledging Customer Issue",
        "required_evidence": [
            "Transaction details and timeline",
            "Support interaction history",
            "Refund processing status",
            "Policy compliance documentation",
        ],
        "key_argument": "The merchant acknowledges the issue and has initiated resolution per policy.",
    },
    "late_delivery": {
        "title": "Late Delivery Dispute — Delivery Eventually Completed",
        "required_evidence": [
            "Original delivery estimate vs actual",
            "Tracking history showing progress",
            "Customer communication about delay",
            "Delivery confirmation",
            "Carrier delay documentation",
        ],
        "key_argument": "While delivery was delayed, the product was ultimately delivered and received.",
    },
    "descriptor_confusion": {
        "title": "Descriptor Confusion — Legitimate Transaction",
        "required_evidence": [
            "Billing descriptor explanation",
            "Transaction authorization details",
            "3DS/OTP verification (if applicable)",
            "Customer purchase history with merchant",
            "Merchant identity documentation",
        ],
        "key_argument": "The transaction was authorized by the cardholder; the billing descriptor is the merchant's registered name.",
    },
    "serial_disputer": {
        "title": "Serial Dispute Pattern — Abuse Detection",
        "required_evidence": [
            "Customer dispute history across transactions",
            "Pattern analysis of previous disputes",
            "Delivery confirmations for past orders",
            "Win/loss record on previous disputes",
            "Account behavior analysis",
        ],
        "key_argument": "The customer has a documented pattern of filing disputes on confirmed deliveries.",
    },
    "cross_border": {
        "title": "Cross-Border Transaction Dispute",
        "required_evidence": [
            "International authorization confirmation",
            "3DS verification record",
            "IP geolocation at time of purchase",
            "Shipping address verification",
            "Customs/import documentation",
        ],
        "key_argument": "The cross-border transaction was properly authorized with additional verification.",
    },
}

# ── Reason Code Database (India-Specific) ─────────────────────────────────

REASON_CODE_DB = {
    "Visa": {
        "10.4": {"name": "Fraud – Card-Absent Environment", "network": "Visa", "deadline_days": 30},
        "13.1": {"name": "Merchandise/Services Not Received", "network": "Visa", "deadline_days": 30},
        "13.3": {"name": "Not as Described", "network": "Visa", "deadline_days": 30},
        "12.4": {"name": "Incorrect Transaction Amount", "network": "Visa", "deadline_days": 30},
        "13.7": {"name": "Cancelled Services", "network": "Visa", "deadline_days": 30},
    },
    "Mastercard": {
        "4837": {"name": "No Cardholder Authorization", "network": "Mastercard", "deadline_days": 45},
        "4855": {"name": "Goods or Services Not Provided", "network": "Mastercard", "deadline_days": 45},
        "4853": {"name": "Cardholder Dispute", "network": "Mastercard", "deadline_days": 45},
        "4834": {"name": "Point of Interaction Error", "network": "Mastercard", "deadline_days": 45},
        "4860": {"name": "Credit Not Processed", "network": "Mastercard", "deadline_days": 45},
    },
    "RuPay": {
        "R01": {"name": "Authorization Related", "network": "RuPay", "deadline_days": 30},
        "R07": {"name": "Goods/Services Not Received", "network": "RuPay", "deadline_days": 30},
        "R08": {"name": "Goods/Services Not as Described", "network": "RuPay", "deadline_days": 30},
        "R04": {"name": "Duplicate Processing", "network": "RuPay", "deadline_days": 30},
        "R09": {"name": "Cancelled/Returned", "network": "RuPay", "deadline_days": 30},
    },
    "UPI": {
        "U01": {"name": "Unauthorized Transaction", "network": "UPI/NPCI", "deadline_days": 10},
        "U05": {"name": "Goods Not Received", "network": "UPI/NPCI", "deadline_days": 10},
        "U06": {"name": "Goods Not as Described", "network": "UPI/NPCI", "deadline_days": 10},
        "U03": {"name": "Duplicate Transaction", "network": "UPI/NPCI", "deadline_days": 10},
        "U07": {"name": "Service Cancelled", "network": "UPI/NPCI", "deadline_days": 10},
    },
}


class EvidenceOrchestrator:
    """
    Generates reason-code-specific evidence packages with compelling narratives.
    Uses LLM for narrative generation, deterministic logic for evidence gathering.
    """

    def __init__(self):
        self.ai_engine = AIEngine()
        self.gemini_model = None
        if HAS_GEMINI and os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    def generate_evidence_package(self, txn: dict, prediction: dict, signals: dict, use_ai: bool = True) -> dict:
        """
        Generate a complete evidence package for a flagged transaction.

        Args:
            txn: Transaction data
            prediction: Model prediction result
            signals: Triggered risk signals
            use_ai: Whether to use remote AI generation (False for fast batch processing)

        Returns:
            Evidence package dict with narrative, checklist, and metadata
        """
        dispute_type = prediction.get("predicted_dispute_type", "friendly_fraud")
        template = EVIDENCE_TEMPLATES.get(dispute_type, EVIDENCE_TEMPLATES["friendly_fraud"])

        # Determine reason code info
        network = txn.get("card_network", "Visa")
        reason_code = txn.get("dispute_reason_code", "")
        reason_info = {}
        if network in REASON_CODE_DB and reason_code in REASON_CODE_DB[network]:
            reason_info = REASON_CODE_DB[network][reason_code]

        # Build evidence checklist (deterministic)
        checklist = self._build_checklist(txn, template)

        # Generate narrative (LLM or template fallback)
        narrative = self._generate_narrative(txn, template, prediction, checklist, reason_info, use_ai=use_ai)

        # Evidence strength score (deterministic)
        strength = self._score_evidence_strength(checklist)

        return {
            "transaction_id": txn.get("payment_id", "unknown"),
            "dispute_type": dispute_type,
            "template_used": template["title"],
            "reason_code": reason_code,
            "reason_code_name": reason_info.get("name", "Unknown"),
            "network": network,
            "deadline_days": reason_info.get("deadline_days", 30),
            "evidence_checklist": checklist,
            "narrative": narrative,
            "evidence_strength": strength,
            "generated_at": datetime.now().isoformat(),
            "generation_method": "groq" if (use_ai and self.ai_engine.is_active) else "template",
        }

    def _build_checklist(self, txn: dict, template: dict) -> list[dict]:
        """Build evidence checklist with availability status."""
        checklist = []
        for item in template["required_evidence"]:
            available = self._check_evidence_available(txn, item)
            checklist.append({
                "item": item,
                "available": available,
                "source": self._get_evidence_source(item),
            })
        return checklist

    def _check_evidence_available(self, txn: dict, item: str) -> bool:
        """Check if a specific piece of evidence is available from transaction data."""
        item_lower = item.lower()
        if "delivery" in item_lower or "tracking" in item_lower:
            return bool(txn.get("has_tracking") in (True, "True", "true"))
        elif "communication" in item_lower or "support" in item_lower:
            return bool(txn.get("contacted_support") in (True, "True", "true"))
        elif "refund" in item_lower:
            return txn.get("refund_status", "none") != "none"
        elif "3ds" in item_lower or "otp" in item_lower or "authorization" in item_lower:
            return True  # Assumed available from payment gateway
        elif "descriptor" in item_lower:
            return True  # Always available
        elif "dispute history" in item_lower or "pattern" in item_lower:
            return int(txn.get("past_disputes", 0)) > 0
        else:
            return True  # Default: available

    def _get_evidence_source(self, item: str) -> str:
        """Determine the source system for evidence."""
        item_lower = item.lower()
        if "delivery" in item_lower or "tracking" in item_lower or "shipping" in item_lower:
            return "Shipping Partner API"
        elif "communication" in item_lower or "support" in item_lower:
            return "CRM / Support System"
        elif "3ds" in item_lower or "otp" in item_lower or "authorization" in item_lower:
            return "Razorpay Payment Gateway"
        elif "refund" in item_lower or "policy" in item_lower:
            return "Merchant Policy DB"
        elif "ip" in item_lower or "geolocation" in item_lower:
            return "Razorpay Transaction Logs"
        elif "dispute history" in item_lower or "pattern" in item_lower:
            return "DisputeForge Analytics"
        else:
            return "Merchant Records"

    def _generate_narrative(
        self, txn: dict, template: dict, prediction: dict,
        checklist: list, reason_info: dict, use_ai: bool = True
    ) -> str:
        """Generate a compelling evidence narrative using LLM or template."""

        # Build context for narrative
        context = {
            "payment_id": txn.get("payment_id"),
            "amount": txn.get("amount"),
            "txn_date": txn.get("txn_date"),
            "merchant": txn.get("merchant_name"),
            "delivery_confirmed": txn.get("delivery_confirmed"),
            "tracking": txn.get("tracking_number"),
            "delivery_date": txn.get("delivery_date"),
            "contacted_support": txn.get("contacted_support"),
            "past_disputes": txn.get("past_disputes"),
            "dispute_probability": prediction.get("dispute_probability"),
            "dispute_type": prediction.get("predicted_dispute_type"),
            "reason_code_name": reason_info.get("name", "Unknown"),
            "available_evidence": [c["item"] for c in checklist if c["available"]],
            "missing_evidence": [c["item"] for c in checklist if not c["available"]],
        }

        if use_ai and self.ai_engine.is_active:
            return self.ai_engine.generate_evidence_narrative(context, template, use_llm=True)
        elif use_ai and self.gemini_model:
            return self._generate_with_gemini(context, template)
        else:
            return self._generate_template_narrative(context, template)

    def _generate_with_gemini(self, context: dict, template: dict) -> str:
        """Generate narrative using Gemini API."""
        prompt = f"""You are an expert chargeback dispute analyst for an Indian payment gateway.
Generate a compelling, professional evidence narrative for a merchant to submit
to the issuing bank to defend against a dispute.

DISPUTE TYPE: {template['title']}
KEY ARGUMENT: {template['key_argument']}

TRANSACTION DETAILS:
- Payment ID: {context['payment_id']}
- Amount: ₹{context['amount']}
- Transaction Date: {context['txn_date']}
- Merchant: {context['merchant']}
- Delivery Confirmed: {context['delivery_confirmed']}
- Tracking Number: {context['tracking']}
- Delivery Date: {context['delivery_date']}
- Customer Contacted Support: {context['contacted_support']}
- Customer's Past Disputes: {context['past_disputes']}
- Dispute Reason: {context['reason_code_name']}

AVAILABLE EVIDENCE: {', '.join(context['available_evidence'])}
MISSING EVIDENCE: {', '.join(context['missing_evidence']) or 'None'}

Write a 3-4 paragraph professional narrative that:
1. States the merchant's position clearly
2. References specific evidence available
3. Addresses the dispute reason directly
4. Concludes with a request to reverse the chargeback

Keep it concise, factual, and persuasive. Use specific details from the transaction.
Do NOT include any headers or formatting — just plain paragraphs."""

        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}. Falling back to template.")
            return self._generate_template_narrative(context, template)

    def _generate_template_narrative(self, context: dict, template: dict) -> str:
        """Generate narrative using templates (fallback when no LLM available)."""
        delivery_status = "confirmed" if context.get("delivery_confirmed") in (True, "True", "true") else "pending verification"
        tracking_info = f"Tracking number {context.get('tracking')}" if context.get("tracking") else "Digital delivery"

        narrative = (
            f"Re: Dispute on Payment {context.get('payment_id', 'N/A')} — "
            f"₹{context.get('amount', 'N/A')} charged on {context.get('txn_date', 'N/A')}\n\n"
            f"We are writing to contest the dispute filed against the above transaction "
            f"with {context.get('merchant', 'our merchant')}. {template['key_argument']}\n\n"
            f"Delivery status: {delivery_status}. {tracking_info}. "
            f"The product was delivered on {context.get('delivery_date', 'N/A')}. "
        )

        if context.get("contacted_support") in (True, "True", "true"):
            narrative += (
                f"The customer contacted our support team prior to filing the dispute. "
            )
        else:
            narrative += (
                f"Notably, the customer did not contact our support team before filing "
                f"this dispute, bypassing our resolution process. "
            )

        past = context.get("past_disputes", 0)
        if past and int(past) > 0:
            narrative += (
                f"\n\nWe note that this customer has filed {past} previous dispute(s), "
                f"indicating a pattern of dispute behavior that warrants scrutiny. "
            )

        evidence_list = context.get("available_evidence", [])
        if evidence_list:
            narrative += (
                f"\n\nThe following evidence is attached to support our case: "
                f"{'; '.join(evidence_list)}. "
            )

        narrative += (
            f"\n\nBased on the evidence provided, we respectfully request that this "
            f"chargeback be reversed in favor of the merchant."
        )

        return narrative

    def _score_evidence_strength(self, checklist: list) -> dict:
        """Score the strength of the evidence package."""
        total = len(checklist)
        available = sum(1 for c in checklist if c["available"])
        score = available / total if total > 0 else 0

        return {
            "score": round(score, 2),
            "available": available,
            "total": total,
            "rating": (
                "strong" if score >= 0.8 else
                "moderate" if score >= 0.6 else
                "weak"
            ),
            "recommendation": (
                "Evidence package is comprehensive. Proceed with submission."
                if score >= 0.8 else
                "Some evidence gaps exist. Consider gathering additional documentation."
                if score >= 0.6 else
                "Significant evidence gaps. Manual review recommended before submission."
            ),
        }
