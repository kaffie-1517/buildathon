# DisputeForge — Architecture Documentation

## System Overview

DisputeForge is a **pre-dispute deflection and evidence orchestration** system that fills the gap in Razorpay's dispute pipeline — acting BEFORE a chargeback is filed, while Razorpay's Dispute Responder acts AFTER.

```
RAZORPAY'S DISPUTE STACK:

    Shield ──► DisputeForge ──► Dispute Responder
    (Block fraud)  (Predict + Deflect)  (Respond after filing)
     Pre-Txn        Pre-Dispute           Post-Dispute
```

## Three-Stage Pipeline

### Stage 1: Risk Signal Extraction (Deterministic)

**File:** `app/risk_engine.py`

Extracts 14 features from transaction data using business rules:

| Signal | Type | Logic |
|:---|:---|:---|
| `delivery_gap` | Binary | delivery_days > 10 |
| `late_delivery` | Continuous | delivery_days / 10 (capped) |
| `refund_requested` | Binary | refund_status != none |
| `high_value` | Binary | amount > ₹5,000 |
| `repeat_disputer` | Continuous | past_disputes / 5 (capped) |
| `descriptor_mismatch` | Binary | billing descriptor ≠ brand name |
| `international` | Binary | card_country ≠ IN |
| `digital_goods` | Binary | no physical delivery proof |
| `no_tracking` | Binary | no tracking number |
| `no_delivery_confirm` | Binary | delivery not confirmed |
| `support_contacted` | Binary | customer contacted support |
| `support_intensity` | Continuous | contacts / 5 (capped) |
| `days_since_delivery` | Continuous | days / 30 (capped) |
| `amount_normalized` | Continuous | amount / 50,000 (capped) |

**Why deterministic?** These are clear business rules — no ambiguity, no judgment needed. Using ML here would be over-engineering.

### Stage 2: Dispute Probability Scoring (ML — XGBoost)

**File:** `app/predictor.py`

- **Model:** XGBoost Gradient Boosted Trees
- **Why XGBoost, not LLM?** Tabular data with clear features → tree-based models consistently outperform LLMs. This demonstrates AI Judgment.
- **Binary classifier:** `dispute_probability: 0.0 → 1.0`
- **Multi-class reason classifier:** Predicts dispute type (friendly_fraud, legitimate, late_delivery, etc.)
- **Training:** 74% train / 26% held-out test split, stratified

### Stage 3: Dual Action Engine

#### Path A — Pre-Dispute Deflection

**File:** `app/deflector.py`

For transactions with `dispute_probability > 0.5`:
- Selects proactive outreach template based on predicted dispute type
- Personalizes message with transaction details
- Sets urgency-based timing (immediate → 48 hours)

#### Path B — Evidence Orchestration

**File:** `app/evidence.py`

For transactions with `dispute_probability > 0.6`:
- Selects evidence template by predicted reason code
- Builds evidence checklist with availability status
- Generates compelling narrative using LLM (Gemini) or template fallback
- Scores evidence strength (strong/moderate/weak)
- Supports India-specific reason codes: Visa, Mastercard, RuPay, UPI

## AI vs. Deterministic Decision Map

| Component | Approach | Rationale |
|:---|:---|:---|
| Risk signals | **Deterministic** | Clear rules, no ambiguity |
| Dispute probability | **ML (XGBoost)** | Tabular data = trees > LLMs |
| Reason code prediction | **ML (Multi-class)** | Classification on structured features |
| Deadline tracking | **Deterministic** | Calendar arithmetic |
| Evidence narrative | **LLM (Gemini)** | Requires contextual reasoning |
| Deflection messages | **Template + personalization** | Structured but personalized |

## Data Flow

```
Transaction Input
    │
    ▼
┌──────────────────────┐
│  Risk Signal Extract  │  ← Deterministic (14 features)
│  (risk_engine.py)     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  XGBoost Predictor    │  ← ML Model
│  (predictor.py)       │
│                       │
│  → dispute_prob       │
│  → risk_level         │
│  → dispute_type       │
└──────┬───────┬───────┘
       │       │
   ≥ 0.5   ≥ 0.6
       │       │
       ▼       ▼
┌──────────┐ ┌─────────────┐
│ Deflector│ │  Evidence    │  ← LLM for narratives
│          │ │  Orchestrator│
└──────────┘ └─────────────┘
       │       │
       ▼       ▼
┌──────────────────────┐
│     Audit Trail       │  ← Every decision logged
│     + Metrics         │
└──────────────────────┘
```

## Metrics Framework

### Binary Classification
- **Precision:** Of flagged transactions, what % actually get disputed?
- **Recall:** Of actual disputes, what % did we catch?
- **F1 Score:** Harmonic mean
- **AUC-ROC:** Area under the curve

### Honest Cost Analysis
- **False Positive Cost:** "For every N disputes caught, M false alarms"
- **Evidence Strength:** Completeness score per evidence package

### What We Get Wrong (Failure Transparency)
- Confusion matrix displayed prominently
- Exception list of misclassified transactions
- Feature importance to explain model decisions

## Synthetic Dataset

270 records with ground truth labels:

| Type | Count | Purpose |
|:---|:---:|:---|
| Clean transactions | 200 | True negatives baseline |
| Friendly fraud | 30 | Primary target (70% of real chargebacks) |
| Legitimate disputes | 15 | Model should NOT flag these aggressively |
| Late delivery | 10 | Deflectable disputes |
| Descriptor confusion | 5 | Preventable disputes |
| Serial disputers | 5 | Pattern detection |
| Cross-border | 5 | Multi-rail testing |

## Tech Stack

| Layer | Technology | Why |
|:---|:---|:---|
| API Server | FastAPI | Async, fast, auto-docs |
| ML | XGBoost + scikit-learn | Right tool for tabular classification |
| LLM | Google Gemini | Evidence narrative generation |
| Dashboard | Vanilla HTML/CSS/JS | No framework overhead, full control |
| Data | pandas + CSV | Simple, reproducible |
| Audit | In-memory JSON | Demo-appropriate (SQLite in production) |
