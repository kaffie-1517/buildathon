"""
DisputeForge — Main API Server

FastAPI application that serves:
1. The analysis pipeline (batch + single transaction)
2. The premium dashboard UI
3. Metrics and audit trail endpoints
"""

import os
import csv
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.risk_engine import extract_risk_signals, get_triggered_signals
from app.predictor import DisputePredictor
from app.evidence import EvidenceOrchestrator
from app.deflector import DeflectionEngine
from app.razorpay_feed import RazorpayFeed

# ── App Setup ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="DisputeForge",
    description="Pre-Dispute Deflection + Intelligent Evidence Orchestrator",
    version="1.0.0",
)

# Mount static files for dashboard
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
if os.path.exists(DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

# Initialize engines
predictor = DisputePredictor()
evidence_engine = EvidenceOrchestrator()
deflection_engine = DeflectionEngine()
razorpay_feed = RazorpayFeed()

# Audit trail (in-memory for demo, would be SQLite/DB in production)
audit_trail = []

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


# ── Models ────────────────────────────────────────────────────────────────

class TransactionInput(BaseModel):
    payment_id: str
    order_id: str = ""
    customer_id: str = ""
    amount: float
    currency: str = "INR"
    txn_date: str = ""
    merchant_name: str = ""
    merchant_category: str = ""
    billing_descriptor: str = ""
    descriptor_matches_brand: bool = True
    card_network: str = "Visa"
    card_country: str = "IN"
    customer_city: str = ""
    is_digital_goods: bool = False
    has_tracking: bool = True
    tracking_number: str = ""
    delivery_days: int = 3
    delivery_date: str = ""
    delivery_confirmed: bool = True
    days_since_delivery: int = 5
    contacted_support: bool = False
    support_contacts_count: int = 0
    past_disputes: int = 0
    past_disputes_won: int = 0
    refund_requested: bool = False
    refund_status: str = "none"


class AnalysisResponse(BaseModel):
    payment_id: str
    risk_signals: dict
    triggered_signals: list
    prediction: dict
    deflection: Optional[dict] = None
    evidence_package: Optional[dict] = None
    audit_entry: dict


# ── Dashboard Route ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard."""
    index_path = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>DisputeForge</h1><p>Dashboard not found. Run from project root.</p>")


# ── API Routes ────────────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_transaction(txn: TransactionInput):
    """Analyze a single transaction for dispute risk."""
    txn_dict = txn.model_dump()
    result = _process_transaction(txn_dict)
    return AnalysisResponse(**result)


@app.post("/api/analyze-single")
async def analyze_single(txn: TransactionInput):
    """Analyze a single transaction — used by the interactive pipeline demo."""
    txn_dict = txn.model_dump()
    result = _process_transaction(txn_dict)
    return JSONResponse(result)



@app.post("/api/analyze-batch")
async def analyze_batch():
    """Analyze the full synthetic dataset batch."""
    csv_path = os.path.join(DATA_DIR, "transactions.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Dataset not found. Run: python data/generate_dataset.py")

    results = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result = _process_transaction(row)
            results.append(result)

    # Compute batch metrics
    total = len(results)
    flagged = [r for r in results if r["prediction"]["risk_level"] in ("high", "critical")]
    deflections = [r for r in results if r.get("deflection")]

    # Compare against ground truth
    ground_truth_disputes = [r for r in results if r.get("_ground_truth_disputed")]
    correctly_flagged = [r for r in flagged if r.get("_ground_truth_disputed")]
    missed = [r for r in results if r.get("_ground_truth_disputed") and r["prediction"]["risk_level"] in ("low", "medium")]
    false_alarms = [r for r in flagged if not r.get("_ground_truth_disputed")]

    tp = len(correctly_flagged)
    fp = len(false_alarms)
    fn = len(missed)
    tn = total - tp - fp - fn

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    batch_metrics = {
        "total_transactions": total,
        "flagged_high_risk": len(flagged),
        "deflections_generated": len(deflections),
        "ground_truth_disputes": len(ground_truth_disputes),
        "correctly_flagged": tp,
        "false_alarms": fp,
        "missed_disputes": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_cost": f"For every {tp} disputes caught, {fp} false alarm(s)" if tp > 0 else "N/A",
    }

    return JSONResponse({
        "batch_metrics": batch_metrics,
        "results": results,
        "analyzed_at": datetime.now().isoformat(),
    })


@app.get("/api/metrics")
async def get_metrics():
    """Get model training metrics."""
    return JSONResponse(predictor.get_metrics())


@app.get("/api/audit-trail")
async def get_audit_trail():
    """Get the audit trail of all analyses."""
    return JSONResponse({"entries": audit_trail, "total": len(audit_trail)})


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": predictor.model is not None,
        "razorpay": razorpay_feed.status(),
    }


@app.get("/api/razorpay/status")
async def razorpay_status():
    """Check Razorpay API connection status."""
    return JSONResponse(razorpay_feed.status())


@app.get("/api/razorpay/test-links")
async def get_test_links():
    """Get active pre-generated test payment links."""
    links_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_payment_links.json")
    if os.path.exists(links_file):
        with open(links_file, "r") as f:
            links = json.load(f)
        return JSONResponse({"links": links})
    return JSONResponse({"links": []})


@app.post("/api/razorpay/create-order")
async def create_checkout_order(request: Request):
    """Create an order for client-side Razorpay checkout."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    amount = float(body.get("amount", 2500))
    merchant = body.get("merchant_name", "Apex Electronics")
    desc = body.get("description", "DisputeForge Sandbox Payment")

    order = razorpay_feed.create_order(
        amount_in_rupees=amount,
        receipt=f"rcpt_{int(datetime.now().timestamp())}",
        notes={"merchant_name": merchant, "description": desc}
    )

    if not order:
        return JSONResponse({"error": "Failed to create Razorpay order"}, status_code=400)

    return JSONResponse({
        "order_id": order.get("id"),
        "amount": order.get("amount"),
        "currency": order.get("currency", "INR"),
        "key_id": razorpay_feed.key_id,
        "merchant_name": merchant,
        "description": desc,
    })


@app.post("/api/razorpay/analyze")
async def analyze_razorpay_payments():
    """
    Fetch live payments from Razorpay test-mode sandbox,
    run each through the DisputeForge pipeline, and return results.
    """
    transactions = razorpay_feed.fetch_recent(count=50)

    if not transactions:
        return JSONResponse({
            "error": "No payments found in Razorpay sandbox. Use 'Create test payment' or pay via one of the sandbox links, then click 'Fetch & analyze'.",
            "razorpay_status": razorpay_feed.status(),
            "results": [],
            "source": "razorpay_live" if razorpay_feed.is_live else "synthetic_fallback",
            "is_test_mode": razorpay_feed.is_test_mode,
            "summary": {
                "total_payments": 0,
                "flagged_high_risk": 0,
                "deflections_generated": 0,
            }
        }, status_code=200)

    results = []
    for txn in transactions:
        result = _process_transaction(txn)
        result["_source"] = txn.get("_source", "razorpay_live")
        result["razorpay_status"] = txn.get("razorpay_status", "")
        result["razorpay_method"] = txn.get("razorpay_method", "")
        results.append(result)

    # Summary stats
    total = len(results)
    flagged = [r for r in results if r["prediction"]["risk_level"] in ("high", "critical")]
    deflections = [r for r in results if r.get("deflection")]

    return JSONResponse({
        "source": "razorpay_live" if razorpay_feed.is_live else "synthetic_fallback",
        "is_test_mode": razorpay_feed.is_test_mode,
        "summary": {
            "total_payments": total,
            "flagged_high_risk": len(flagged),
            "deflections_generated": len(deflections),
        },
        "results": results,
        "analyzed_at": datetime.now().isoformat(),
    })


# ── Internal Processing ───────────────────────────────────────────────────

def _process_transaction(txn: dict) -> dict:
    """Process a single transaction through the full pipeline."""

    # Stage 1: Extract risk signals (deterministic)
    signals = extract_risk_signals(txn)
    triggered = get_triggered_signals(signals)

    # Stage 2: Predict dispute probability (ML)
    prediction = predictor.predict(signals)

    # Stage 3a: Generate deflection if high risk
    deflection = None
    if prediction["dispute_probability"] >= 0.5:
        deflection = deflection_engine.generate_deflection(txn, prediction)

    # Stage 3b: Generate evidence package if high risk
    evidence = None
    if prediction["dispute_probability"] >= 0.6:
        evidence = evidence_engine.generate_evidence_package(txn, prediction, triggered)

    # Audit trail entry
    audit_entry = {
        "payment_id": txn.get("payment_id", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "dispute_probability": prediction["dispute_probability"],
        "risk_level": prediction["risk_level"],
        "signals_triggered": len(triggered),
        "deflection_generated": deflection is not None,
        "evidence_generated": evidence is not None,
        "model_used": prediction.get("model_used", "unknown"),
    }
    audit_trail.append(audit_entry)

    # Check ground truth (for batch metrics)
    is_actually_disputed = txn.get("dispute_filed") in (True, "True", "true", "1", 1)

    return {
        "payment_id": txn.get("payment_id", "unknown"),
        "amount": txn.get("amount"),
        "merchant_name": txn.get("merchant_name"),
        "card_network": txn.get("card_network"),
        "risk_signals": signals.to_dict(),
        "triggered_signals": triggered,
        "prediction": prediction,
        "deflection": deflection,
        "evidence_package": evidence,
        "audit_entry": audit_entry,
        "_ground_truth_disputed": is_actually_disputed,
        "_ground_truth_type": txn.get("dispute_type", "none"),
    }
