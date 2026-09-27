# Magicpin AI Challenge (Vera) — Master Project & Handoff Guide

> **For any LLM or Developer reading this file**: This document contains the complete state, architecture, dataset instructions, API contract, and roadmap for building the **Vera Message Engine** for the Magicpin AI Challenge. You can pick up the work immediately by following the steps below.

---

## 1. Executive Summary

- **Challenge**: India's Biggest AI Challenge by magicpin — Build the message engine behind **Vera** (magicpin's WhatsApp AI assistant for retail merchant growth).
- **Target Verticals**: 5 categories — `dentists`, `salons`, `restaurants`, `gyms`, `pharmacies`.
- **Core Functionality**:
  1. Maintain stateful multi-layer context across categories, merchants, customers, and triggers.
  2. Implement proactive messaging (`POST /v1/tick`) choosing the best trigger, creating specific, compelling WhatsApp copy with a single clear CTA.
  3. Implement conversation reply handling (`POST /v1/reply`) to handle accepts, objections, delays, and crucially **canned WhatsApp Business auto-replies** (which make up 40-70% of incoming merchant messages).
  4. Expose 5 standard HTTP endpoints adhering strictly to the challenge testing brief.
  5. Achieve 9-10/10 scores across all 5 evaluation dimensions on the official `judge_simulator.py`.

---

## 2. Directory Structure & Key Files

```
c:/Users/DEV ISSRANI/Desktop/MagicPin Challenge/
├── challenge-brief.md            # Detailed business & product requirements
├── challenge-testing-brief.md    # Technical HTTP API contract and JSON schemas
├── engagement-design.md          # WhatsApp conversation UX patterns & best practices
├── engagement-research.md        # Research insights, benchmark data, and failure modes
├── judge_simulator.py            # Official local LLM evaluation test harness
├── dataset/
│   ├── categories/               # Knowledge packs for the 5 verticals
│   ├── merchants_seed.json       # 10 merchant seeds (expands to 50)
│   ├── customers_seed.json       # 15 customer seeds (expands to 200)
│   ├── triggers_seed.json        # 25 trigger seeds (expands to 100)
│   └── generate_dataset.py       # Deterministic dataset generator (30 canonical pairs)
├── examples/
│   ├── api-call-examples.md      # Concrete curl & payload examples for all endpoints
│   └── case-studies.md           # 10 scored benchmark examples showing rubric criteria
└── PROJECT_HANDOFF.md            # (This file) Complete handoff & continuity guide
```

---

## 3. The 5 Required API Endpoints

All endpoints accept and return JSON. The server should run on port `8080` (or configurable).

### 3.1 `POST /v1/context` (Context Ingestion & State Update)
- **Request**:
  ```json
  {
    "scope": "category" | "merchant" | "customer" | "trigger",
    "context_id": "dentists",
    "version": 1,
    "payload": { ... },
    "delivered_at": "2026-04-26T10:00:00Z"
  }
  ```
- **Rules**:
  - Idempotent by `(context_id, version)`. Re-posting same version is a 200 OK no-op.
  - Higher version atomically replaces prior state (200 OK).
  - Stale/lower version returns `409 Conflict` (`{ "accepted": false, "reason": "stale_version", "current_version": N }`).
  - Response 200: `{ "accepted": true, "ack_id": "ack_xxx", "stored_at": "..." }`.

### 3.2 `POST /v1/tick` (Proactive Outbound Evaluation)
- **Request**:
  ```json
  {
    "now": "2026-04-26T10:30:00Z",
    "available_triggers": ["trg_2026_04_26_research_digest", "trg_2026_04_26_recall_priya"]
  }
  ```
- **Response**:
  ```json
  {
    "actions": [
      {
        "conversation_id": "conv_001",
        "merchant_id": "m_001_drmeera",
        "customer_id": null,
        "send_as": "vera",
        "trigger_id": "trg_2026_04_26_research_digest",
        "template_name": "vera_research_digest_v1",
        "template_params": ["Dr. Meera", "JIDA Oct issue"],
        "body": "Dr. Meera, 190 people in Lajpat Nagar are searching for Dental Check Up...",
        "cta": "binary_yes_no",
        "suppression_key": "research:dentists:2026-W17",
        "rationale": "High-urgency local demand trigger combined with Dr. Meera's active cleaning offer."
      }
    ]
  }
  ```
  *(Return empty `{"actions": []}` if no trigger warrants proactive messaging).*

### 3.3 `POST /v1/reply` (Conversational Turn Handling)
- **Request**:
  ```json
  {
    "conversation_id": "conv_001",
    "merchant_id": "m_001_drmeera",
    "customer_id": null,
    "from_role": "merchant",
    "message": "Yes, send details",
    "received_at": "2026-04-26T10:45:00Z",
    "turn_number": 2
  }
  ```
- **Response**:
  - `send`: `{ "action": "send", "body": "...", "cta": "open_ended", "rationale": "..." }`
  - `wait`: `{ "action": "wait", "wait_seconds": 1800, "rationale": "..." }`
  - `end`: `{ "action": "end", "rationale": "..." }`

### 3.4 `GET /v1/healthz`
- Response: `{ "status": "ok", "timestamp": "...", "uptime_seconds": 120 }`

### 3.5 `GET /v1/metadata`
- Response:
  ```json
  {
    "bot_name": "Vera-Engine",
    "version": "1.0.0",
    "author": "Candidate",
    "supported_categories": ["dentists", "salons", "restaurants", "gyms", "pharmacies"],
    "capabilities": ["proactive_tick", "reply_handling", "auto_reply_filter", "context_grounded"]
  }
  ```

---

## 4. The 5 Evaluation Rubric Dimensions (Scored 0–10 each)

1. **Decision Quality (0–10)**: Selects highest-ROI trigger given merchant performance and prior conversation behavior.
2. **Specificity (0–10)**: Strict grounding in real numbers, rupee pricing (`₹299`), dates, and local facts (zero hallucination).
3. **Category Fit (0–10)**: Tone matched to vertical:
   - *Dentists*: Clinical peer tone, evidence-based, taboo words avoided ("cure", "guaranteed").
   - *Salons*: Visual, style-forward, seasonal (bridal, weekend).
   - *Restaurants*: Foodie excitement, dish-focused, weekend/dinner spikes.
   - *Gyms*: Motivational, fitness goals, seasonal (New Year, post-festive).
   - *Pharmacies*: Utility, medicine availability, health camps, compliance.
4. **Merchant Fit (0–10)**: Uses merchant's real offer catalog and addresses specific gaps (e.g. low CTR, stale photos).
5. **Engagement Compulsion (0–10)**: One clear reason to reply + one simple low-friction CTA (e.g. simple Yes/No).

---

## 5. Critical Technical Nuances & Solutions

1. **Auto-Reply Detection**:
   - Merchants often have WhatsApp automated replies like *"Thank you for contacting Dr. X's clinic. We will get back shortly."*
   - Solution: Auto-reply regex + intent classifier. Do not treat as merchant agreement; either send a polite confirmation or wait for real human response.
2. **Suppression Windows**:
   - Track `suppression_key` with expiration timestamps to prevent spamming merchants with the same trigger twice.
3. **Deterministic & Fast Response**:
   - Latency must be well under the 30-second judge timeout (ideally < 2 seconds).

---

## 6. Current Implementation State & Achievements

- **Dataset**: Expanded seeds to 50 merchants, 200 customers, 100 triggers, 30 canonical test pairs in `expanded/`.
- **Server**: FastAPI application in `engine/server.py` and `main.py` running on port 8000 (`http://127.0.0.1:8000`).
- **Context Store**: In-memory thread-safe state store in `engine/store.py` with version tracking and suppression management.
- **Message Composer**: `engine/composer.py` powered by Groq LLM (`openai/gpt-oss-120b`) with linked digest item resolution and deterministic grounded fallbacks.
- **Intent Classifier**: `engine/intent.py` handling WhatsApp Business canned auto-replies, hostiles/opt-outs, and immediate action transitions.
- **Judge Simulator Tests**:
  - `python judge_simulator.py all` -> **100% PASS** (warmup, auto_reply, intent, hostile).
  - `python judge_simulator.py phase2_short` -> **Scoring up to 40/50 (80%+)** across all 5 rubric dimensions.

---

## 7. Public Live URL & Submission Information

- **Live Public Bot URL**: `https://whereas-monitored-named-explanation.trycloudflare.com`
- **Healthz Check**: `https://whereas-monitored-named-explanation.trycloudflare.com/v1/healthz`
- **Metadata Check**: `https://whereas-monitored-named-explanation.trycloudflare.com/v1/metadata`
- **Remote Judge Verification**: Tested with official `judge_simulator.py` over the live public URL (`100% PASS` across all scenarios, up to `43/50` score).

### How to Submit:
1. Open the [Magicpin Submission Form](https://partners.magicpin.com/vera/ai-challenge/#submit).
2. Enter your details:
   - **Full name**: Dev Issrani
   - **Email**: (Your email)
   - **Phone number**: (Your phone number)
   - **Submission URL**: `https://whereas-monitored-named-explanation.trycloudflare.com`
   - **LinkedIn URL**: (Optional)
3. Click **Submit details**.
4. **Important**: Keep the server and tunnel active so the magicpin judge harness can perform evaluation passes on fresh scenarios!

---

## 8. Prompt Template to Resume with Any LLM

If you switch to another LLM, simply copy and paste this prompt:

```text
I am working on the Magicpin AI Challenge (Vera Message Engine).
Please read `PROJECT_HANDOFF.md` in my project root.
Phase 1 and Phase 2 are complete and verified with judge_simulator.py.
Current Goal: Expose the local FastAPI server via a public URL (e.g. ngrok / cloudflare / render) and finalize the submission details.
```
