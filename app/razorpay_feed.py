"""
DisputeForge — Razorpay Live Feed
===================================
Fetches real payments from Razorpay test-mode sandbox and maps
them to DisputeForge's risk pipeline format.

Handles:
- Payment fetch via Razorpay Python SDK
- Field mapping from Razorpay schema → DisputeForge schema
- Dispute/refund status enrichment
- Graceful fallback when API keys not set

Usage:
    from app.razorpay_feed import RazorpayFeed
    feed = RazorpayFeed()
    transactions = feed.fetch_recent(count=50)
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Optional import — graceful if razorpay not installed
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False


class RazorpayFeed:
    """
    Fetches and normalises Razorpay payments for the DisputeForge pipeline.
    Works in test-mode (rzp_test_*) or live-mode keys.
    Falls back to synthetic data when keys are absent.
    """

    # Card networks Razorpay returns
    NETWORK_MAP = {
        "Visa": "Visa",
        "MasterCard": "Mastercard",
        "Maestro": "Mastercard",
        "RuPay": "RuPay",
        "American Express": "Amex",
        "Diners Club": "Diners",
        "unknown": "Visa",   # default for demo
    }

    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
        self._client = None
        self.is_live = bool(self.key_id and self.key_secret and RAZORPAY_AVAILABLE)
        self.is_test_mode = self.key_id.startswith("rzp_test_") if self.key_id else False

        if self.is_live:
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def status(self) -> dict:
        return {
            "sdk_available": RAZORPAY_AVAILABLE,
            "keys_configured": bool(self.key_id and self.key_secret),
            "is_live": self.is_live,
            "is_test_mode": self.is_test_mode,
            "key_id_prefix": self.key_id[:12] + "…" if len(self.key_id) > 12 else self.key_id,
        }

    def fetch_recent(self, count: int = 50) -> list[dict]:
        """
        Fetch recent payments from Razorpay API and normalise to
        DisputeForge transaction format.

        Falls back to synthetic demo data if keys not configured.
        """
        if not self.is_live:
            return self._fallback_data(count)

        try:
            response = self._client.payment.all({
                "count": min(count, 100),   # Razorpay max is 100 per call
                "skip": 0,
            })
            payments = response.get("items", [])
            return [self._normalise(p) for p in payments]

        except Exception as e:
            print(f"[RazorpayFeed] API error: {e} — falling back to synthetic data")
            return self._fallback_data(count)

    def fetch_payment(self, payment_id: str) -> Optional[dict]:
        """Fetch a single payment by ID."""
        if not self.is_live:
            return None
        try:
            p = self._client.payment.fetch(payment_id)
            return self._normalise(p)
        except Exception as e:
            print(f"[RazorpayFeed] Could not fetch {payment_id}: {e}")
            return None

    def fetch_disputes(self, count: int = 20) -> list[dict]:
        """
        Fetch existing disputes from Razorpay.
        Used to build ground truth labels for precision/recall.
        """
        if not self.is_live:
            return []
        try:
            response = self._client.dispute.all({"count": count})
            return response.get("items", [])
        except Exception as e:
            print(f"[RazorpayFeed] Could not fetch disputes: {e}")
            return []

    # ── Normalisation ─────────────────────────────────────────────────────

    def _normalise(self, p: dict) -> dict:
        """
        Map a Razorpay payment object → DisputeForge transaction schema.

        Razorpay payment fields reference:
        https://razorpay.com/docs/api/payments/
        """
        # Amount in paise → rupees
        amount = p.get("amount", 0) / 100.0

        # Timestamps
        created_at = p.get("created_at", 0)
        txn_dt = datetime.fromtimestamp(created_at, tz=timezone.utc) if created_at else datetime.now(timezone.utc)
        txn_date = txn_dt.strftime("%Y-%m-%d")

        # Card details
        card = p.get("card") or {}
        network_raw = card.get("network", "unknown")
        network = self.NETWORK_MAP.get(network_raw, "Visa")
        card_country = card.get("international", False)

        # Method (card/upi/netbanking/wallet)
        method = p.get("method", "card")
        is_digital = method in ("upi", "wallet")

        # Acquirer data / notes
        notes = p.get("notes") or {}
        desc = p.get("description") or ""

        # Refund/dispute signals from Razorpay status
        rzp_status = p.get("status", "captured")    # authorized/captured/refunded/failed
        refund_status_map = {
            "refunded": "full",
            "partially_refunded": "partial",
            "captured": "none",
            "authorized": "none",
            "failed": "none",
        }
        refund_status = refund_status_map.get(rzp_status, "none")
        refund_requested = refund_status in ("full", "partial")

        # Dispute status from Razorpay dispute field (if present)
        dispute_filed = p.get("dispute_filed", False) or rzp_status == "disputed"

        # Descriptor match heuristic — compare merchant name to billing desc
        merchant_name = (
            notes.get("merchant_name")
            or p.get("merchant_display_name")
            or "Razorpay Merchant"
        )
        billing_descriptor = desc or merchant_name
        descriptor_matches = _fuzzy_match(merchant_name, billing_descriptor)

        # Delivery heuristics — infer from method and category
        # Real integration would pull from merchant's fulfillment API
        # For demo: digital goods deliver instantly, physical goods 3-7 days
        delivery_days = 1 if is_digital else self._infer_delivery_days(p)
        delivery_confirmed = is_digital   # digital = immediate

        return {
            # Razorpay native fields (shown in demo)
            "payment_id": p.get("id", f"pay_demo_{created_at}"),
            "order_id": p.get("order_id") or "",
            "razorpay_status": rzp_status,
            "razorpay_method": method,

            # Core transaction fields
            "amount": round(amount, 2),
            "currency": p.get("currency", "INR"),
            "txn_date": txn_date,
            "merchant_name": merchant_name,
            "billing_descriptor": billing_descriptor,
            "descriptor_matches_brand": descriptor_matches,
            "card_network": network,
            "card_country": "IN" if not card_country else card.get("issuer", "US"),
            "is_digital_goods": is_digital,

            # Delivery signals
            "delivery_days": delivery_days,
            "delivery_confirmed": delivery_confirmed,
            "has_tracking": not is_digital,
            "tracking_number": "",
            "delivery_date": "",
            "days_since_delivery": max(0, (datetime.now(timezone.utc) - txn_dt).days - delivery_days),

            # Risk signals
            "past_disputes": 0,    # Would need customer-level aggregation
            "contacted_support": False,
            "support_contacts_count": 0,
            "refund_requested": refund_requested,
            "refund_status": refund_status,

            # Ground truth (known from Razorpay dispute status)
            "dispute_filed": dispute_filed,
            "dispute_type": "razorpay_dispute" if dispute_filed else "none",

            # Source metadata
            "_source": "razorpay_live",
            "_fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _infer_delivery_days(self, p: dict) -> int:
        """
        Infer expected delivery days from payment category/notes.
        Real integration would pull from merchant fulfillment API.
        """
        notes = p.get("notes") or {}
        category = str(notes.get("category", "")).lower()

        delivery_map = {
            "electronics": 5,
            "fashion": 7,
            "grocery": 1,
            "food": 0,
            "travel": 0,
            "software": 0,
            "subscription": 0,
        }
        for key, days in delivery_map.items():
            if key in category:
                return days

        return 5  # default: 5-day physical delivery

    # ── Fallback synthetic data ───────────────────────────────────────────

    def _fallback_data(self, count: int) -> list[dict]:
        """
        Return synthetic transactions that LOOK like Razorpay payments.
        Used when no API keys are configured.
        Includes realistic pay_* IDs and Razorpay field structure.
        """
        import csv, os
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "transactions.csv"
        )
        if not os.path.exists(csv_path):
            return []

        results = []
        with open(csv_path, encoding="utf-8") as f:
            for row in list(csv.DictReader(f))[:count]:
                row["_source"] = "synthetic_fallback"
                results.append(row)
        return results


# ── Helpers ──────────────────────────────────────────────────────────────

def _fuzzy_match(a: str, b: str) -> bool:
    """
    Simple descriptor match — checks if key words from merchant name
    appear in the billing descriptor.
    """
    def tokens(s):
        return set(re.sub(r"[^a-z0-9 ]", "", s.lower()).split())

    a_tok = tokens(a)
    b_tok = tokens(b)
    if not a_tok or not b_tok:
        return True
    overlap = a_tok & b_tok
    return len(overlap) / max(len(a_tok), 1) > 0.3
