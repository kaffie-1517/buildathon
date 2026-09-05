"""
DisputeForge — AI Engine (Groq LPU Inference)
=============================================
Powers real-time generative intelligence:
1. Contextual Pre-Dispute Deflection Copywriting
2. Card-Network Compliant Evidence Rebuttal Narratives
3. Executive AI Risk Explainability & Merchant Action Recommendations

Powered by Groq's LPU inference engine for ultra-low latency (<500ms).
"""

import os
import json
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class AIEngine:
    """
    Central AI engine using Groq for low-latency generative risk intelligence.
    """

    DEFAULT_MODELS = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
        "groq/compound-mini",
    ]

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.is_active = bool(self.api_key and GROQ_AVAILABLE)
        self.client = None
        self.active_model = self.DEFAULT_MODELS[0]

        if self.is_active:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"[AIEngine] Failed to init Groq client: {e}")
                self.is_active = False

    def status(self) -> dict:
        return {
            "available": GROQ_AVAILABLE,
            "configured": bool(self.api_key),
            "is_active": self.is_active,
            "provider": "Groq LPU",
            "model": self.active_model,
        }

    def _parse_amount(self, val) -> float:
        try:
            return float(val or 0)
        except (ValueError, TypeError):
            return 0.0

    # ── 1. Real-Time Deflection Copywriting ───────────────────────────────

    def generate_deflection(self, context: dict, use_llm: bool = True) -> dict:
        """
        Generate a personalized, contextual pre-dispute outreach message.
        """
        if not use_llm or not self.is_active or not self.client:
            return self._fallback_deflection(context)

        merchant = context.get("merchant_name", "Merchant Store")
        amount = self._parse_amount(context.get("amount", 0))
        dispute_type = context.get("predicted_dispute_type", "friendly_fraud")
        delivery_days = context.get("delivery_days", 3)
        delivery_confirmed = context.get("delivery_confirmed", True)
        refund_status = context.get("refund_status", "none")
        support_contacts = context.get("support_contacts_count", 0)
        order_id = context.get("order_id") or context.get("payment_id", "ORD-1092")
        customer_name = context.get("customer_name", "Customer")
        raw_signals = context.get("triggered_signals", [])
        signals = [(s.get("description") or s.get("signal") or str(s)) if isinstance(s, dict) else str(s) for s in raw_signals]

        prompt = f"""You are DisputeForge AI, an expert pre-dispute retention and chargeback mitigation system for Razorpay merchants.

Goal: Write a proactive, highly personalized outreach message to the customer to resolve their concern BEFORE they file a bank chargeback.

Transaction Details:
- Merchant Name: {merchant}
- Order ID: {order_id}
- Transaction Amount: INR {amount:,.2f}
- Customer Name: {customer_name}
- Predicted Dispute Risk: {dispute_type}
- Delivery Status: {'Delivered in ' + str(delivery_days) + ' days' if delivery_confirmed else 'In transit (' + str(delivery_days) + ' days)'}
- Refund Request Status: {refund_status}
- Prior Support Contacts: {support_contacts}
- Triggered Signals: {', '.join(signals) if signals else 'None'}

Rules:
1. Tone matching:
   - For 'friendly_fraud': Firm, polite, confirm delivery proof and tracking, offer direct customer support channel so they don't claim unauthorized or goods-not-received to their bank.
   - For 'late_delivery': Empathetic, sincere apology for transit delay, offer shipping compensation or priority resolution.
   - For 'descriptor_confusion': Clarify the billing descriptor as it appears on their card statement vs the brand name they know.
2. Return ONLY a JSON object (no markdown, no backticks, no extra text) with these exact keys:
   - "subject": email subject line (concise, engaging)
   - "body": 2-3 paragraph professional message
   - "tone": e.g. "Empathetic & Resolution-Oriented" or "Reassuring & Transparent"
   - "channel": "email" or "sms_and_email"
   - "ai_reasoning": 1-2 sentences explaining why this exact communication strategy defuses the impending chargeback.
"""

        t0 = time.time()
        for model in self.DEFAULT_MODELS:
            try:
                res = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a specialized fintech AI risk agent. Return ONLY raw JSON without code blocks or conversational text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=450
                )
                raw = res.choices[0].message.content.strip()
                parsed = self._clean_and_parse_json(raw)
                if parsed and "subject" in parsed and "body" in parsed:
                    latency = int((time.time() - t0) * 1000)
                    return {
                        "subject": parsed["subject"],
                        "body": parsed["body"],
                        "tone": parsed.get("tone", "Empathetic"),
                        "channel": parsed.get("channel", "email"),
                        "ai_reasoning": parsed.get("ai_reasoning", "Tailored to address customer uncertainty and prevent escalation to card issuer."),
                        "is_ai_generated": True,
                        "generated_by": f"Groq ({model})",
                        "latency_ms": latency,
                    }
            except Exception as e:
                print(f"[AIEngine] Model {model} deflection generation error: {e}")
                continue

        return self._fallback_deflection(context)

    # ── 2. Evidence Narrative Generation ─────────────────────────────────

    def generate_evidence_narrative(self, context: dict, template: dict, use_llm: bool = True) -> str:
        """
        Generate an executive, bank-grade dispute rebuttal narrative.
        """
        if not use_llm or not self.is_active or not self.client:
            return self._fallback_narrative(context, template)

        merchant = context.get("merchant_name", "Merchant Store")
        amount = self._parse_amount(context.get("amount", 0))
        pay_id = context.get("payment_id", "pay_xxxx")
        txn_date = context.get("txn_date", "recent")
        network = context.get("card_network", "Visa")
        reason_code = template.get("code", "10.4")
        reason_name = template.get("name", "Product Not Received")
        delivery_confirmed = context.get("delivery_confirmed", True)
        delivery_days = context.get("delivery_days", 3)
        tracking = context.get("tracking_number", "TRK-98214")

        prompt = f"""You are DisputeForge Legal & Risk AI, drafting an official representation narrative to the acquiring bank and card network ({network}) to successfully overturn a chargeback.

Dispute Details:
- Merchant: {merchant}
- Payment ID: {pay_id}
- Transaction Amount: INR {amount:,.2f}
- Transaction Date: {txn_date}
- Network: {network}
- Reason Code: {reason_code} - {reason_name}
- Delivery Confirmation: {'Confirmed delivered in ' + str(delivery_days) + ' days via tracking ' + tracking if delivery_confirmed else 'Package dispatched with active tracking ' + tracking}

Draft a formal 2-3 paragraph rebuttal letter:
- State clearly that the merchant fulfilled all terms of sale in accordance with card network guidelines.
- Point to specific evidence: delivery confirmation, matching billing records, and zero prior merchant support escalation.
- Request the issuing bank to reverse the chargeback in the merchant favor.

Return ONLY the narrative text, professional and authoritative."""

        for model in self.DEFAULT_MODELS:
            try:
                res = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional banking compliance officer drafting dispute representation evidence."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=500
                )
                narrative = res.choices[0].message.content.strip()
                if len(narrative) > 50:
                    return narrative
            except Exception as e:
                print(f"[AIEngine] Model {model} narrative error: {e}")
                continue

        return self._fallback_narrative(context, template)

    # ── 3. Real-Time AI Risk Explainability ──────────────────────────────

    def generate_risk_insight(self, context: dict, risk_score: float, triggered_signals: list, use_llm: bool = True) -> dict:
        """
        Generate an executive AI risk explanation explaining *why* the transaction was flagged
        and giving merchants immediate tactical instructions.
        """
        if not use_llm or not self.is_active or not self.client:
            return self._fallback_insight(risk_score, triggered_signals)

        merchant = context.get("merchant_name", "Merchant")
        amount = self._parse_amount(context.get("amount", 0))
        prob_pct = f"{risk_score * 100:.1f}%"
        sig_list = [(s.get("description") or s.get("signal") or str(s)) if isinstance(s, dict) else str(s) for s in (triggered_signals or [])]
        signals_str = ", ".join(sig_list) if sig_list else "No anomalous signals"

        prompt = f"""You are DisputeForge AI Risk Advisor.
Analyze this transaction scored by our XGBoost model:
- Merchant: {merchant}
- Amount: INR {amount:,.2f}
- XGBoost Dispute Probability: {prob_pct}
- Triggered Signals: {signals_str}

Return ONLY a JSON object (no markdown, no backticks) with:
- "executive_summary": 1 punchy sentence explaining why this transaction is dangerous or clean.
- "primary_vulnerability": 3-6 words describing the main weak point (e.g. "Unaddressed delivery delay", "High-velocity refund abuse pattern", "Descriptor brand mismatch").
- "merchant_action": 1 specific, actionable step the merchant should take right now.
"""

        for model in self.DEFAULT_MODELS:
            try:
                res = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a fintech risk analyst. Return ONLY raw valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=250
                )
                raw = res.choices[0].message.content.strip()
                parsed = self._clean_and_parse_json(raw)
                if parsed and "executive_summary" in parsed:
                    return {
                        "executive_summary": parsed["executive_summary"],
                        "primary_vulnerability": parsed.get("primary_vulnerability", "Pattern matches prior chargebacks"),
                        "merchant_action": parsed.get("merchant_action", "Initiate proactive customer outreach"),
                        "model": f"Groq ({model})",
                    }
            except Exception as e:
                continue

        return self._fallback_insight(risk_score, triggered_signals)

    # ── Helpers & Fallbacks ──────────────────────────────────────────────

    def _clean_and_parse_json(self, text: str) -> Optional[dict]:
        t = text.strip()
        if t.startswith("```json"):
            t = t[7:]
        elif t.startswith("```"):
            t = t[3:]
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
        try:
            return json.loads(t)
        except Exception:
            return None

    def _fallback_deflection(self, context: dict) -> dict:
        merchant = context.get("merchant_name", "our store")
        amount = self._parse_amount(context.get("amount", 0))
        order_id = context.get("order_id") or context.get("payment_id", "your order")
        return {
            "subject": f"Quick update on your order from {merchant}",
            "body": f"Hello! We are following up regarding your recent transaction of INR {amount:,.2f} (Order #{order_id}). If you have any questions or concerns regarding this order, please reply directly to this message so we can assist you immediately without any need to contact your bank.",
            "tone": "Warm & Reassuring",
            "channel": "email",
            "ai_reasoning": "Proactively verifies delivery and provides instant support channel to deter chargeback initiation.",
            "is_ai_generated": False,
            "generated_by": "Heuristic Rule Engine (Offline Fallback)",
            "latency_ms": 1,
        }

    def _fallback_narrative(self, context: dict, template: dict) -> str:
        merchant = context.get("merchant_name", "Merchant")
        pay_id = context.get("payment_id", "pay_xxxx")
        amount = self._parse_amount(context.get("amount", 0))
        network = context.get("card_network", "Visa")
        code = template.get("code", "10.4")
        return (
            f"This representation evidence package formally refutes the dispute for payment {pay_id} "
            f"amounting to INR {amount:,.2f}. The cardholder engaged with {merchant} and authorized the transaction. "
            f"Merchant fulfilled all sale terms in compliance with {network} chargeback guidelines for reason code {code}. "
            f"Attached documentation provides conclusive evidence of order completion and delivery verification."
        )

    def _fallback_insight(self, score: float, signals: list) -> dict:
        if score > 0.7:
            return {
                "executive_summary": "High risk of post-fulfillment chargeback due to compounding negative customer and delivery signals.",
                "primary_vulnerability": "Compounded dispute indicators",
                "merchant_action": "Send immediate proactive deflection email and prepare proof of delivery.",
                "model": "DisputeForge Rule Engine",
            }
        elif score > 0.3:
            return {
                "executive_summary": "Moderate dispute probability primarily driven by delivery delays or support contacts.",
                "primary_vulnerability": "Customer fulfillment friction",
                "merchant_action": "Reach out to customer with tracking update or courtesy compensation.",
                "model": "DisputeForge Rule Engine",
            }
        else:
            return {
                "executive_summary": "Transaction exhibits healthy behavioral and delivery metrics with negligible dispute risk.",
                "primary_vulnerability": "None detected",
                "merchant_action": "No merchant intervention required.",
                "model": "DisputeForge Rule Engine",
            }
