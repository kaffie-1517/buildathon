# DisputeForge

**Pre-Dispute Deflection and Intelligent Evidence Orchestration for Razorpay**

> The best chargeback is the one that never happens.

DisputeForge is an intelligent pre-dispute risk engine that identifies dispute-likely transactions before a bank chargeback is filed, deflects customer disputes through proactive personalized outreach, and pre-assembles card-network-compliant evidence packages.

Built for the Razorpay AI Buildathon 2026 — Track 2: AI Risk Manager.

---

## Problem

- In Indian e-commerce, over 70% of chargebacks stem from "friendly fraud" — where a customer received the package or service but disputes the charge with their issuing bank.
- Razorpay Shield blocks known fraud before checkout, while Razorpay Dispute Responder manages evidence after a formal chargeback notification is issued.
- A critical blind spot exists in between: the post-fulfillment, pre-dispute window where disputes brew without merchant visibility or proactive intervention.
- Merchants lose 2-3x the transaction value per dispute when factoring in processor dispute fees, chargeback penalties, lost inventory, and gateway dispute ratio thresholds.

---

## Solution

DisputeForge operates in the post-transaction, pre-dispute window, bridging Razorpay Shield and Dispute Responder:

```
Razorpay Shield            DisputeForge                       Dispute Responder
(Pre-checkout fraud) ──► (Predict + Deflect + Prepare) ──► (Post-chargeback defense)
```

### Three-Stage Pipeline

1. **Risk Signal Extraction (Deterministic):** Extracts 14 domain-specific risk signals across fulfillment timelines, delivery confirmations, refund inquiries, billing descriptor clarity, customer support interactions, and historical dispute velocity.
2. **Dispute Probability Scoring (XGBoost ML):** Gradient-boosted decision tree ensemble trained on structured transactional features, scoring dispute probability in 2 milliseconds.
3. **Generative AI Dual-Action Engine (Groq LPU):**
   - **AI Risk Explainability:** Generates plain-English executive summaries, primary vulnerability breakdowns, and merchant tactical actions.
   - **Pre-Dispute Deflection:** Generates personalized outreach copy with dynamic tone matching (firm delivery confirmation vs. empathetic delay resolution) and strategic reasoning.
   - **Evidence Orchestration:** Generates reason-code-specific representation letters formatted according to Visa, Mastercard, and RuPay scheme bylaws.

---

## Architecture

```
+-------------------------------------------------------------------------+
|                              DATA INGESTION                             |
|    Razorpay Sandbox Live API (client.payment.all) / CSV Batch Dataset   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  STAGE 1: RISK SIGNAL EXTRACTOR (Rules)                 |
|    14 Signals: delivery_gap, descriptor_mismatch, refund_status, etc.   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  STAGE 2: DISPUTE PREDICTOR (XGBoost ML)                |
|    Dispute Probability: 0.0 - 1.0 (Tabular Tree Classification)         |
+------------------+------------------------------------+-----------------+
                   |                                    |
                   v                                    v
+------------------------------------+   +--------------------------------+
|  STAGE 2b: AI RISK ADVISOR (Groq)  |   |  STAGE 3a: DEFLECTION (Groq)   |
|  Executive Risk Summary & Actions  |   |  Proactive outreach copy with  |
+------------------------------------+   |  dynamic tone & reasoning      |
                                         +--------------------------------+
                                                        |
                                                        v
                                         +--------------------------------+
                                         |  STAGE 3b: EVIDENCE (Groq)     |
                                         |  Reason-code evidence packages |
                                         |  and card-network narratives   |
                                         +--------------------------------+
                                                        |
                                                        v
+-------------------------------------------------------------------------+
|                        AUDIT TRAIL AND METRICS                          |
|    Precision: 92.5% | Recall: 88.6% | F1: 0.905 | False Alarm Analysis  |
+-------------------------------------------------------------------------+
```

---

## Method Selection (Why Each Tool Was Chosen)

| Stage | Approach | Rationale |
|:---|:---|:---|
| Risk Signal Extraction | Deterministic Rules | 14 domain rules; zero ambiguity, 100% reproducible. |
| Dispute Probability | XGBoost ML | Decision trees consistently outperform LLMs on tabular numerical data (2ms latency). |
| Reason Code Classification | Multi-class XGBoost | Structured network categorization based on signal vectors. |
| Deadlines and SLA Tracking | Deterministic Rules | Strict scheme calendar math (Visa 30d, Mastercard 45d, RuPay 30d, UPI 10d). |
| AI Risk Explainability | Groq LPU (qwen3.8-27b) | Contextual plain-English merchant summary and vulnerability diagnosis (<1s). |
| Deflection Copywriting | Groq LPU (qwen3.8-27b) | Empathetic tone matching and strategic rationale (<1s). |
| Evidence Narrative | Groq LPU (qwen3.8-27b) | Formal legal representation text compliant with card network standards. |

---

## Razorpay Integration

DisputeForge includes direct integration with Razorpay's Python SDK and test-mode sandbox:

- **Live Payment Ingestion:** Calls `client.payment.all()` to pull real `pay_*` entities directly from Razorpay.
- **Embedded Sandbox Checkout:** In-dashboard Razorpay Checkout helper allowing one-click test payments using test cards, UPI, or simulated Netbanking.
- **Acquirer Note and Descriptor Mapping:** Reconciles gateway payment methods, billing descriptors, and refund statuses into the dispute feature matrix.
- **Inspection Drawer:** Deep inspection of any live payment with its raw payload, XGBoost risk score, and auto-generated Groq deflection draft.

---

## Evaluation Metrics

Evaluated on a 270-transaction benchmark dataset across 6 dispute categories:

- **Precision:** 92.5% (92 out of 100 flagged transactions are genuine dispute risks).
- **Recall:** 88.6% (captures nearly 9 out of 10 disputes before filing).
- **F1 Score:** 0.905.
- **False Positive Cost:** Only 5 false alarms across 200 clean transactions. Tuned specifically to avoid alert fatigue and protect customer trust.

---

## Tech Stack

| Layer | Component |
|:---|:---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Machine Learning | XGBoost, scikit-learn, NumPy, pandas |
| Generative AI | Groq Python SDK (qwen/qwen3.8-27b, sub-second LPU inference) |
| Payment Gateway | Razorpay Python SDK (`razorpay>=1.4.2`) |
| Frontend | Vanilla HTML5, CSS3 (Custom Design System), Modern JavaScript |
| Data | Synthetic benchmark dataset (270 transactions, 14 features) |

---

## Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone and Install
```bash
git clone https://github.com/kaffie-1517/buildathon.git
cd buildathon
python3 -m pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Configure your API keys in `.env`:
```ini
# Groq API Key (powers real-time AI Risk Advisor, deflection, and evidence)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Razorpay Test Mode Keys (powers live sandbox ingestion and checkout)
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

### 4. Train Model and Generate Dataset
```bash
python3 data/generate_dataset.py
python3 model/train.py
```

### 5. Start the Server
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.

---

## Project Structure

```
buildathon/
├── app/
│   ├── main.py              # FastAPI server, endpoints, and dashboard routes
│   ├── ai_engine.py         # Groq LPU inference engine (explainability, deflection, evidence)
│   ├── predictor.py         # XGBoost model loader and inference pipeline
│   ├── razorpay_feed.py     # Razorpay Python SDK client and sandbox ingestion
│   ├── risk_engine.py       # 14 deterministic risk signals extractor
│   ├── deflector.py         # Pre-dispute deflection orchestrator
│   └── evidence.py          # Reason-code evidence assembler
├── model/
│   └── train.py             # XGBoost model training and evaluation script
├── data/
│   ├── generate_dataset.py  # Synthetic benchmark dataset generator
│   └── transactions.csv     # 270 benchmark transactions with ground truth
├── dashboard/
│   ├── index.html           # Interactive pipeline and live feed UI
│   ├── style.css            # Custom dark/light responsive design system
│   └── app.js               # Frontend controller, checkout integration, and animation
├── tests/
│   └── test_pipeline.py     # End-to-end integration and unit tests
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variable template
└── README.md                # Project documentation
```

---

## Author

**Jasmeet Singh** — [GitHub](https://github.com/kaffie-1517)

---

## License

MIT License
