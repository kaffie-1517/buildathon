"""
DisputeForge — Synthetic Dispute Dataset Generator

Generates a realistic dataset of 270 transactions with ground truth labels
for training and evaluating the dispute prediction model.

Categories:
- 200 clean transactions (no dispute)
- 30 friendly fraud (received but claims not)
- 15 legitimate disputes (real issues)
- 10 late delivery disputes
- 5 descriptor confusion disputes
- 5 serial disputer patterns
- 5 cross-border disputes

Each record includes realistic transaction metadata, delivery info,
customer history, and dispute outcomes.
"""

import csv
import random
import os
from datetime import datetime, timedelta


random.seed(42)  # Reproducibility

# ── Constants ─────────────────────────────────────────────────────────────

MERCHANTS = [
    {"name": "QuickMart Electronics", "descriptor": "QKMART*ELECTRONICS", "category": "electronics"},
    {"name": "FreshBasket Groceries", "descriptor": "FRESHBSKT*GROC", "category": "groceries"},
    {"name": "StyleHub Fashion", "descriptor": "STYLHUB*FASHION", "category": "fashion"},
    {"name": "BookNest Online", "descriptor": "BKNEST*ONLINE", "category": "books"},
    {"name": "FitGear Sports", "descriptor": "FITGEAR*SPORTS", "category": "sports"},
    {"name": "PixelCraft Digital", "descriptor": "PXLCRFT*DIGITAL", "category": "digital"},
]

CARD_NETWORKS = ["Visa", "Mastercard", "RuPay", "UPI"]

REASON_CODES = {
    "Visa": {
        "fraud": "10.4", "not_received": "13.1", "not_as_described": "13.3",
        "duplicate": "12.4", "cancelled": "13.7"
    },
    "Mastercard": {
        "fraud": "4837", "not_received": "4855", "not_as_described": "4853",
        "duplicate": "4834", "cancelled": "4860"
    },
    "RuPay": {
        "fraud": "R01", "not_received": "R07", "not_as_described": "R08",
        "duplicate": "R04", "cancelled": "R09"
    },
    "UPI": {
        "fraud": "U01", "not_received": "U05", "not_as_described": "U06",
        "duplicate": "U03", "cancelled": "U07"
    },
}

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Kochi", "Indore", "Nagpur", "Bhopal",
]

INTL_COUNTRIES = ["US", "UK", "SG", "AE", "DE"]

BASE_DATE = datetime(2026, 8, 1)


# ── Helper Functions ──────────────────────────────────────────────────────

def gen_payment_id():
    return f"pay_{random.randint(10**13, 10**14 - 1)}"


def gen_order_id():
    return f"order_{random.randint(10**11, 10**12 - 1)}"


def gen_customer_id():
    return f"cust_{random.randint(10000, 99999)}"


def random_date(start, end):
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def gen_tracking():
    carriers = ["BlueDart", "Delhivery", "DTDC", "Ecom Express", "India Post"]
    return f"{random.choice(carriers)}-{random.randint(100000000, 999999999)}"


def gen_transaction(
    label,
    dispute_type=None,
    reason_category=None,
    dispute_outcome=None,
    force_params=None,
):
    """Generate a single transaction record with all fields."""
    params = force_params or {}

    merchant = params.get("merchant", random.choice(MERCHANTS))
    network = params.get("network", random.choices(
        CARD_NETWORKS, weights=[35, 25, 25, 15], k=1
    )[0])

    # Transaction date
    txn_date = params.get("txn_date", random_date(BASE_DATE, BASE_DATE + timedelta(days=25)))

    # Amount distribution based on type
    if dispute_type == "friendly_fraud":
        amount = random.choice([
            round(random.uniform(500, 3000), 2),   # Mid-range most common
            round(random.uniform(3000, 15000), 2),  # Higher value targets
        ])
    elif dispute_type == "high_value":
        amount = round(random.uniform(8000, 50000), 2)
    else:
        amount = round(random.uniform(99, 8000), 2)

    amount = params.get("amount", amount)

    # Customer
    customer_id = params.get("customer_id", gen_customer_id())
    is_international = params.get("is_international", False)
    card_country = params.get("card_country", random.choice(INTL_COUNTRIES) if is_international else "IN")
    customer_city = params.get("customer_city", random.choice(CITIES))

    # Delivery info
    is_digital = merchant["category"] == "digital"
    has_tracking = params.get("has_tracking", not is_digital and random.random() > 0.05)
    tracking_number = gen_tracking() if has_tracking else None

    delivery_days = params.get("delivery_days", random.randint(1, 7) if not is_digital else 0)
    delivery_date = txn_date + timedelta(days=delivery_days) if not is_digital else txn_date
    delivery_confirmed = params.get("delivery_confirmed", True if has_tracking and random.random() > 0.08 else False)

    # Customer contact history
    contacted_support = params.get("contacted_support", random.random() < 0.15)
    support_contacts_count = params.get("support_contacts_count", random.randint(1, 4) if contacted_support else 0)

    # Customer dispute history
    past_disputes = params.get("past_disputes", 0)
    past_disputes_won = params.get("past_disputes_won", 0)

    # Refund info
    refund_requested = params.get("refund_requested", False)
    refund_status = params.get("refund_status", "none")

    # Billing descriptor match
    descriptor_matches_brand = params.get(
        "descriptor_matches_brand",
        random.random() > 0.12  # 12% descriptor mismatch rate
    )

    # Days since delivery (for dispute timing)
    days_since_delivery = params.get(
        "days_since_delivery",
        random.randint(0, 45)
    )

    # Dispute fields
    if label == "no_dispute":
        dispute_filed = False
        dispute_date = None
        dispute_reason_code = None
        dispute_outcome_val = None
    else:
        dispute_filed = True
        dispute_days_after = random.randint(3, 30)
        dispute_date = (delivery_date + timedelta(days=dispute_days_after)).strftime("%Y-%m-%d")
        rc_category = reason_category or random.choice(["fraud", "not_received", "not_as_described"])
        dispute_reason_code = REASON_CODES[network][rc_category]
        dispute_outcome_val = dispute_outcome or random.choice(["won", "lost"])

    return {
        "payment_id": gen_payment_id(),
        "order_id": gen_order_id(),
        "customer_id": customer_id,
        "amount": amount,
        "currency": "INR",
        "txn_date": txn_date.strftime("%Y-%m-%d"),
        "merchant_name": merchant["name"],
        "merchant_category": merchant["category"],
        "billing_descriptor": merchant["descriptor"],
        "descriptor_matches_brand": descriptor_matches_brand,
        "card_network": network,
        "card_country": card_country,
        "customer_city": customer_city,
        "is_digital_goods": is_digital,
        "has_tracking": has_tracking,
        "tracking_number": tracking_number or "",
        "delivery_days": delivery_days,
        "delivery_date": delivery_date.strftime("%Y-%m-%d"),
        "delivery_confirmed": delivery_confirmed,
        "days_since_delivery": days_since_delivery,
        "contacted_support": contacted_support,
        "support_contacts_count": support_contacts_count,
        "past_disputes": past_disputes,
        "past_disputes_won": past_disputes_won,
        "refund_requested": refund_requested,
        "refund_status": refund_status,
        # Labels
        "dispute_filed": dispute_filed,
        "dispute_type": dispute_type or "none",
        "dispute_date": dispute_date or "",
        "dispute_reason_code": dispute_reason_code or "",
        "dispute_outcome": dispute_outcome_val or "",
    }


# ── Dataset Generation ────────────────────────────────────────────────────

def generate_dataset():
    """Generate the full 270-record synthetic dataset."""
    records = []

    # ── 200 clean transactions (no dispute) ──
    for _ in range(200):
        records.append(gen_transaction("no_dispute"))

    # ── 30 friendly fraud (received but claims not) ──
    for _ in range(30):
        records.append(gen_transaction(
            label="dispute",
            dispute_type="friendly_fraud",
            reason_category="not_received",
            dispute_outcome=random.choice(["won", "lost", "lost"]),  # Merchants lose more
            force_params={
                "delivery_confirmed": True,         # Key: they DID receive it
                "has_tracking": True,
                "contacted_support": random.random() < 0.3,  # Rarely contact support
                "days_since_delivery": random.randint(10, 30),
            },
        ))

    # ── 15 legitimate disputes (real issues) ──
    for _ in range(15):
        issue_type = random.choice(["not_received", "not_as_described", "duplicate"])
        records.append(gen_transaction(
            label="dispute",
            dispute_type="legitimate",
            reason_category=issue_type,
            dispute_outcome="won",  # Customer wins legitimate disputes
            force_params={
                "delivery_confirmed": issue_type != "not_received",
                "contacted_support": True,  # Legit customers contact support
                "support_contacts_count": random.randint(2, 5),
                "refund_requested": True,
                "refund_status": random.choice(["pending", "denied"]),
            },
        ))

    # ── 10 late delivery → dispute ──
    for _ in range(10):
        records.append(gen_transaction(
            label="dispute",
            dispute_type="late_delivery",
            reason_category="not_received",
            dispute_outcome=random.choice(["won", "lost"]),
            force_params={
                "delivery_days": random.randint(12, 30),  # Very late
                "delivery_confirmed": random.random() < 0.5,
                "contacted_support": True,
                "support_contacts_count": random.randint(2, 6),
                "days_since_delivery": random.randint(5, 15),
            },
        ))

    # ── 5 descriptor confusion disputes ──
    for _ in range(5):
        records.append(gen_transaction(
            label="dispute",
            dispute_type="descriptor_confusion",
            reason_category="fraud",  # Customer thinks it's fraud because descriptor is confusing
            dispute_outcome="lost",   # Merchant wins with proof
            force_params={
                "descriptor_matches_brand": False,  # Key: confusing descriptor
                "delivery_confirmed": True,
                "contacted_support": False,  # They go straight to bank
                "days_since_delivery": random.randint(15, 45),
            },
        ))

    # ── 5 serial disputer patterns ──
    serial_customer = gen_customer_id()
    for i in range(5):
        records.append(gen_transaction(
            label="dispute",
            dispute_type="serial_disputer",
            reason_category=random.choice(["not_received", "fraud"]),
            dispute_outcome=random.choice(["won", "lost"]),
            force_params={
                "customer_id": serial_customer,
                "past_disputes": i + 2,  # Growing history
                "past_disputes_won": i + 1,
                "delivery_confirmed": True,
                "contacted_support": False,
                "days_since_delivery": random.randint(7, 20),
            },
        ))

    # ── 5 cross-border disputes ──
    for _ in range(5):
        records.append(gen_transaction(
            label="dispute",
            dispute_type="cross_border",
            reason_category=random.choice(["fraud", "not_received"]),
            dispute_outcome=random.choice(["won", "lost"]),
            force_params={
                "is_international": True,
                "card_country": random.choice(INTL_COUNTRIES),
                "amount": round(random.uniform(5000, 25000), 2),
                "days_since_delivery": random.randint(10, 35),
            },
        ))

    # Shuffle to avoid ordering bias
    random.shuffle(records)
    return records


def save_dataset(records, filepath):
    """Save records to CSV."""
    if not records:
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    fieldnames = records[0].keys()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"✅ Generated {len(records)} records → {filepath}")

    # Print summary
    dispute_count = sum(1 for r in records if r["dispute_filed"])
    clean_count = len(records) - dispute_count
    print(f"   Clean transactions: {clean_count}")
    print(f"   Disputed transactions: {dispute_count}")

    # Breakdown by type
    types = {}
    for r in records:
        t = r["dispute_type"]
        types[t] = types.get(t, 0) + 1
    for t, c in sorted(types.items()):
        if t != "none":
            print(f"     → {t}: {c}")


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__))
    records = generate_dataset()
    save_dataset(records, os.path.join(data_dir, "transactions.csv"))
