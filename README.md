# DisputeForge 🛡️

**Pre-Dispute Deflection + Intelligent Evidence Orchestrator**

> The best chargeback is the one that never happens.

DisputeForge is an AI-powered agent that identifies dispute-likely transactions **before** the chargeback is filed, generates reason-code-specific evidence packages, and measures its precision/recall honestly.

Built for [Razorpay AI Buildathon 2026](https://razorpay.com/buildathon/) — **Track 2: AI Risk Manager**

---

## 🎯 Problem

- **70% of chargebacks** in Indian e-commerce are "friendly fraud" — the customer received the product but claims they didn't
- Razorpay's Dispute Responder acts **after** the chargeback is filed
- **Nobody fills the gap before** — predicting, deflecting, and preparing evidence proactively
- Merchants lose **2-3x the transaction value** per chargeback (refund + penalty + lost goods)

## 💡 Solution

DisputeForge sits between Razorpay Shield (fraud prevention) and Razorpay Dispute Responder (post-chargeback):

```
Shield ──► DisputeForge ──► Dispute Responder
(Block fraud)  (Predict + Deflect + Prepare)  (Respond after filing)
```

### Three-Stage Pipeline

1. **Risk Signal Extraction** (Deterministic) — 8 rule-based signals that predict disputes
2. **Dispute Probability Scoring** (XGBoost ML) — Gradient boosted trees on tabular data
3. **Dual Action Engine**:
   - **Deflection**: Proactive customer outreach to resolve before chargeback
   - **Evidence Preparation**: Reason-code-specific evidence packages with LLM-generated narratives

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    DATA SOURCES                       │
│  Transactions │ Delivery Data │ Comms │ History       │
└───────────┬──────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           RISK SIGNAL EXTRACTOR (Deterministic)       │
│  delivery_gap │ refund_requested │ high_value │ ...   │
└───────────┬──────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           DISPUTE PREDICTOR (XGBoost)                 │
│  dispute_probability: 0.0 → 1.0                      │
│  threshold: > 0.7 → HIGH RISK                        │
└───────┬───────────────────────────┬──────────────────┘
        │                           │
        ▼                           ▼
┌───────────────────┐   ┌──────────────────────────────┐
│  DEFLECTION       │   │  EVIDENCE ORCHESTRATOR        │
│  ENGINE           │   │  (LLM-powered)                │
│                   │   │                                │
│  Proactive        │   │  Reason-code-specific          │
│  customer         │   │  evidence packages with        │
│  outreach         │   │  compelling narratives          │
└───────────────────┘   └──────────────────────────────┘
            │                           │
            ▼                           ▼
┌──────────────────────────────────────────────────────┐
│              AUDIT TRAIL + METRICS                    │
│  Every prediction, action, and decision logged        │
│  Precision │ Recall │ F1 │ False Positive Cost        │
└──────────────────────────────────────────────────────┘
```

## 🧠 AI Judgment (When AI vs. Deterministic)

| Task | Approach | Why |
|:---|:---|:---|
| Risk signal extraction | **Deterministic** | Clear rules, no ambiguity |
| Dispute probability | **ML (XGBoost)** | Tabular data = tree models outperform LLMs |
| Reason code prediction | **ML (Multi-class)** | Classification on structured features |
| Deadline tracking | **Deterministic** | Calendar math, not judgment |
| Evidence narrative | **LLM (Gemini)** | Requires reasoning about context |
| Deflection messages | **LLM (Gemini)** | Requires empathy and personalization |

## 📊 Metrics (Honest)

- **Precision**: Of flagged transactions, what % actually get disputed?
- **Recall**: Of actual disputes, what % did we catch beforehand?
- **F1 Score**: Harmonic mean of precision and recall
- **False Positive Cost**: For every real dispute prevented, how many false alarms?
- **Evidence Quality**: Completeness score of auto-generated packages

## 🛠️ Tech Stack

| Component | Technology |
|:---|:---|
| Backend | Python + FastAPI |
| ML Model | XGBoost |
| Evidence Generation | Google Gemini API |
| Frontend | HTML + CSS + JavaScript |
| Data | Synthetic dataset (270 records) |
| Metrics | scikit-learn |
| Audit Trail | SQLite + JSON |

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/kaffie-1517/buildathon.git
cd buildathon

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# Generate synthetic data
python data/generate_dataset.py

# Train model
python model/train.py

# Run server
python -m uvicorn app.main:app --reload

# Open dashboard
open http://localhost:8000
```

## 📁 Project Structure

```
buildathon/
├── app/                    # FastAPI application
│   ├── main.py            # API server + dashboard
│   ├── risk_engine.py     # Risk signal extraction
│   ├── predictor.py       # XGBoost dispute predictor
│   ├── evidence.py        # LLM evidence orchestrator
│   └── deflector.py       # Pre-dispute deflection
├── model/
│   └── train.py           # Model training pipeline
├── data/
│   ├── generate_dataset.py # Synthetic data generator
│   └── transactions.csv   # Generated dataset
├── dashboard/
│   ├── index.html         # Main dashboard
│   ├── style.css          # Styles
│   └── app.js             # Dashboard logic
├── tests/
│   └── test_pipeline.py   # Pipeline tests
├── requirements.txt
├── .env.example
└── README.md
```

## 👤 Author

**Jasmeet Singh** — [@kaffie-1517](https://github.com/kaffie-1517)

## 📄 License

MIT
