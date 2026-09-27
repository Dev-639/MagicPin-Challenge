"""
FastAPI Server for Vera Engine implementing the 5 challenge endpoints + Live Interactive UI Dashboard.
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, HTMLResponse
from engine.store import store
from engine.composer import compose
from engine.intent import handle_reply

app = FastAPI(
    title="Vera Message Engine",
    description="magicpin AI Assistant for Merchant Growth",
    version="1.0.0"
)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>magicpin Vera AI — Live Engine Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(23, 32, 54, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #00d084;
      --primary-glow: rgba(0, 208, 132, 0.3);
      --accent: #38bdf8;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --wa-bg: #0b141a;
      --wa-bubble-in: #202c33;
      --wa-bubble-out: #005c4b;
      --wa-accent: #00a884;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: radial-gradient(circle at 50% 0%, #172554 0%, #0b0f19 75%);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 28px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-badge {
      background: linear-gradient(135deg, #00d084, #06b6d4);
      color: #000;
      font-weight: 800;
      font-size: 14px;
      padding: 6px 12px;
      border-radius: 8px;
      font-family: 'Outfit', sans-serif;
      letter-spacing: 0.5px;
    }

    h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 208, 132, 0.1);
      border: 1px solid rgba(0, 208, 132, 0.3);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 500;
      color: var(--primary);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      background: var(--primary);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--primary);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.2); }
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }

    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }

    .card-title {
      font-family: 'Outfit', sans-serif;
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    select, input, textarea {
      width: 100%;
      background: rgba(11, 15, 25, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 10px 14px;
      color: var(--text);
      font-size: 14px;
      font-family: 'Inter', sans-serif;
      outline: none;
      transition: all 0.2s;
    }

    select:focus, input:focus, textarea:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }

    button {
      background: linear-gradient(135deg, #00d084, #059669);
      color: #000;
      border: none;
      font-weight: 600;
      font-size: 14px;
      padding: 12px 20px;
      border-radius: 10px;
      cursor: pointer;
      width: 100%;
      transition: transform 0.15s, box-shadow 0.15s;
    }

    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px var(--primary-glow);
    }

    button:active {
      transform: translateY(1px);
    }

    /* WhatsApp Chat Preview */
    .wa-preview {
      background: var(--wa-bg);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid rgba(255,255,255,0.05);
      min-height: 260px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      gap: 12px;
      background-image: radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 16px 16px;
    }

    .wa-bubble {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.45;
      position: relative;
    }

    .wa-bubble.out {
      align-self: flex-start;
      background: var(--wa-bubble-in);
      color: var(--text);
      border-top-left-radius: 0;
    }

    .wa-bubble.in {
      align-self: flex-end;
      background: var(--wa-bubble-out);
      color: #e9edef;
      border-top-right-radius: 0;
    }

    .wa-meta {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
      margin-top: 4px;
      text-align: right;
    }

    .wa-cta-btn {
      display: inline-block;
      margin-top: 8px;
      padding: 6px 12px;
      background: rgba(0, 168, 132, 0.2);
      border: 1px solid var(--wa-accent);
      color: var(--wa-accent);
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }

    pre.json-box {
      background: #060911;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #38bdf8;
      max-height: 200px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    .endpoints-nav {
      display: flex;
      gap: 10px;
      margin-top: 24px;
      flex-wrap: wrap;
    }

    .ep-badge {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-muted);
      text-decoration: none;
      transition: 0.2s;
    }

    .ep-badge:hover {
      background: rgba(0, 208, 132, 0.1);
      border-color: var(--primary);
      color: var(--primary);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-badge">MAGICPIN VERA</div>
        <div>
          <h1>AI Assistant Message Engine</h1>
          <p style="font-size: 13px; color: var(--text-muted);">Deterministic context-grounded merchant assistant</p>
        </div>
      </div>
      <div class="status-pill">
        <div class="status-dot"></div>
        <span id="liveStatus">Engine Online (Port 8000)</span>
      </div>
    </header>

    <div class="grid">
      <!-- 1. Proactive Tick Simulation -->
      <div class="card">
        <div class="card-title">
          <span>1. Proactive Trigger & Composition</span>
          <span style="font-size: 12px; color: var(--primary); font-family: 'JetBrains Mono';">POST /v1/tick</span>
        </div>
        <div class="form-group">
          <label>Select Scenario & Trigger</label>
          <select id="triggerSelect">
            <option value="trg_001_research_digest_dentists">Dentist: JIDA Research Digest (Fluoride Study)</option>
            <option value="trg_002_compliance_dci_radiograph">Dentist: DCI Regulatory Compliance Alert</option>
            <option value="trg_003_recall_due_priya">Customer: Priya 6-Month Dental Recall</option>
            <option value="trg_004_perf_dip_bharat">Dentist: Performance Dip (-50% Calls)</option>
            <option value="trg_007_bridal_followup_kavya">Salon: Bridal Skin-Prep Followup (196 Days)</option>
            <option value="trg_010_ipl_match_delhi">Restaurant: IPL Match Night Special</option>
            <option value="trg_012_milestone_mylari">Restaurant: Milestone Review Reached (145/150)</option>
            <option value="trg_020_summer_demand_shift">Pharmacy: Summer Hydration Demand Shift</option>
          </select>
        </div>
        <button onclick="runTick()">Simulate Proactive Tick</button>
        
        <div style="margin-top: 18px;">
          <label>API Response & Decision Rationale</label>
          <pre id="tickResponse" class="json-box">Click "Simulate Proactive Tick" to view composed message...</pre>
        </div>
      </div>

      <!-- 2. WhatsApp Live Message Preview -->
      <div class="card">
        <div class="card-title">
          <span>Live WhatsApp Conversation Preview</span>
          <span style="font-size: 12px; color: var(--text-muted);">Vera ↔ Merchant / Customer</span>
        </div>
        
        <div class="wa-preview" id="chatWindow">
          <div class="wa-bubble out" id="msgVera">
            <strong style="color: var(--primary); display: block; margin-bottom: 2px;">Vera</strong>
            Select a trigger on the left to see the message Vera will compose for the merchant.
            <div class="wa-meta">10:30 AM</div>
          </div>
        </div>

        <div style="margin-top: 18px;">
          <div class="card-title" style="font-size: 15px; margin-bottom: 8px;">
            <span>2. Test Conversational Reply Handling</span>
            <span style="font-size: 12px; color: var(--accent); font-family: 'JetBrains Mono';">POST /v1/reply</span>
          </div>
          <div class="form-group" style="display: flex; gap: 8px; margin-bottom: 0;">
            <input type="text" id="replyInput" placeholder="Type: 'Yes lets do it' / 'Stop' / Auto-reply..." value="Ok lets do it. Whats next?">
            <button style="width: 140px;" onclick="sendReply()">Send</button>
          </div>
        </div>
      </div>
    </div>

    <div class="endpoints-nav">
      <a href="/v1/healthz" target="_blank" class="ep-badge">GET /v1/healthz</a>
      <a href="/v1/metadata" target="_blank" class="ep-badge">GET /v1/metadata</a>
      <a href="/docs" target="_blank" class="ep-badge" style="border-color: var(--accent); color: var(--accent);">Swagger OpenAPI Docs (/docs)</a>
    </div>
  </div>

  <script>
    async function runTick() {
      const triggerId = document.getElementById('triggerSelect').value;
      document.getElementById('tickResponse').innerText = "Querying Vera Composer Engine...";
      
      try {
        const res = await fetch('/v1/tick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            now: new Date().toISOString(),
            available_triggers: [triggerId]
          })
        });
        const data = await res.json();
        document.getElementById('tickResponse').innerText = JSON.stringify(data, null, 2);

        if (data.actions && data.actions.length > 0) {
          const action = data.actions[0];
          document.getElementById('chatWindow').innerHTML = `
            <div class="wa-bubble out">
              <strong style="color: var(--primary); display: block; margin-bottom: 4px;">${action.send_as === 'vera' ? 'Vera' : 'Dr. Meera'}</strong>
              ${action.body}
              <div><span class="wa-cta-btn">CTA: ${action.cta}</span></div>
              <div class="wa-meta">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} ✓✓</div>
            </div>
          `;
        }
      } catch (e) {
        document.getElementById('tickResponse').innerText = "Error: " + e.message;
      }
    }

    async function sendReply() {
      const msg = document.getElementById('replyInput').value;
      if (!msg) return;

      const chat = document.getElementById('chatWindow');
      chat.innerHTML += `
        <div class="wa-bubble in">
          ${msg}
          <div class="wa-meta">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} ✓✓</div>
        </div>
      `;

      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: "conv_interactive_demo",
            merchant_id: "m_001_drmeera_dentist_delhi",
            from_role: "merchant",
            message: msg,
            turn_number: 2
          })
        });
        const data = await res.json();
        
        let responseText = data.body || `[Action: ${data.action.toUpperCase()}] — ${data.rationale}`;
        chat.innerHTML += `
          <div class="wa-bubble out">
            <strong style="color: var(--primary); display: block; margin-bottom: 4px;">Vera</strong>
            ${responseText}
            <div class="wa-meta">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} ✓✓</div>
          </div>
        `;
      } catch (e) {
        console.error(e);
      }
    }

    // Auto-run first tick on load
    window.onload = () => {
      runTick();
    };
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)


@app.get("/v1/healthz")
async def healthz():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": store.get_uptime_seconds()
    }


@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Dev Issrani",
        "bot_name": "Vera AI Message Engine",
        "version": "1.0.0",
        "model": "openai/gpt-oss-120b",
        "supported_categories": ["dentists", "salons", "restaurants", "gyms", "pharmacies"],
        "capabilities": [
            "proactive_tick",
            "context_grounded_composition",
            "multi_turn_reply_handling",
            "auto_reply_loop_prevention",
            "hostile_opt_out_graceful_exit",
            "commitment_action_transition"
        ]
    }


@app.post("/v1/context")
async def receive_context(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_json"}
        )

    scope = data.get("scope")
    context_id = data.get("context_id")
    version = data.get("version", 1)
    payload = data.get("payload", {})

    if not scope or not context_id or scope not in ["category", "merchant", "customer", "trigger"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_scope", "details": f"Scope '{scope}' is invalid"}
        )

    accepted, error_reason, cur_ver = store.save_context(scope, context_id, version, payload)

    if not accepted:
        if error_reason == "stale_version":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"accepted": False, "reason": "stale_version", "current_version": cur_ver}
            )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": error_reason}
        )

    return {
        "accepted": True,
        "ack_id": f"ack_{uuid.uuid4().hex[:8]}",
        "stored_at": datetime.now(timezone.utc).isoformat()
    }


@app.post("/v1/tick")
async def handle_tick(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    available_triggers = data.get("available_triggers", [])

    # ── Phase 1: Resolve all trigger + merchant + customer payloads ──────────────
    resolved = []
    for trigger_id in available_triggers:
        trigger_payload = store.get_context("trigger", trigger_id)
        if not trigger_payload:
            trigger_payload = _load_trigger_from_seed(trigger_id)
        if not trigger_payload:
            continue

        merchant_id = trigger_payload.get("merchant_id")
        merchant_payload = None
        if merchant_id:
            merchant_payload = store.get_context("merchant", merchant_id)
        if not merchant_payload and merchant_id:
            merchant_payload = _load_merchant_from_seed(merchant_id)
        if not merchant_payload:
            all_merchants = store.get_all("merchant")
            if all_merchants:
                trigger_cat = trigger_payload.get("payload", {}).get("category", "")
                for mid, m in all_merchants.items():
                    if m.get("category_slug") == trigger_cat:
                        merchant_id = mid
                        merchant_payload = m
                        break
                if not merchant_payload:
                    merchant_id = list(all_merchants.keys())[0]
                    merchant_payload = all_merchants[merchant_id]
        if not merchant_payload:
            continue

        cat_slug = merchant_payload.get("category_slug", "dentists")
        category_payload = store.get_context("category", cat_slug)
        if not category_payload:
            category_payload = _load_category_from_seed(cat_slug)
        if not category_payload:
            category_payload = {"slug": cat_slug}

        customer_id = trigger_payload.get("customer_id")
        customer_payload = None
        if customer_id:
            customer_payload = store.get_context("customer", customer_id)
            if not customer_payload:
                customer_payload = _load_customer_from_seed(customer_id)

        resolved.append({
            "trigger_id": trigger_id,
            "trigger": trigger_payload,
            "merchant": merchant_payload,
            "category": category_payload,
            "customer": customer_payload,
        })

    # ── Phase 2: Rank by Decision Quality (urgency + ROI kind) ──────────────────
    URGENCY_SCORE = {"high": 3, "medium": 2, "low": 1}
    # Kinds that represent the highest immediate ROI, in priority order
    KIND_PRIORITY = [
        "recall", "refill", "appointment", "booking",    # customer-facing — highest ROI
        "perf_dip", "competitor",                        # urgent merchant performance
        "supply_alert", "regulation", "compliance",      # compliance / supply urgency
        "winback", "lapsed",                             # re-engagement
        "festival", "ipl", "milestone",                  # time-bound events
        "perf_spike", "review_theme",                    # positive / moderate
        "research_digest", "cde", "webinar",             # informational
        "renewal", "dormant", "planning",                # low-urgency engagement
        "seasonal", "curious_ask", "gbp_unverified",     # background
    ]

    def _trigger_sort_key(item: dict) -> tuple:
        t = item["trigger"]
        raw_urgency = t.get("urgency") or "low"
        # urgency may be an int (3=high, 2=medium, 1=low) or a string
        if isinstance(raw_urgency, int):
            urgency = raw_urgency  # already numeric — use directly
        else:
            urgency = URGENCY_SCORE.get(str(raw_urgency).lower(), 0)
        kind = (t.get("kind") or "").lower()
        # Find position in priority list (lower index = higher priority)
        kind_rank = next(
            (i for i, k in enumerate(KIND_PRIORITY) if k in kind),
            len(KIND_PRIORITY)  # unknown kinds go last
        )
        # Customer-facing triggers always beat merchant-facing at the same urgency
        is_customer = 1 if (t.get("scope") == "customer" or t.get("customer_id")) else 0
        # Sort: urgency DESC, is_customer DESC, kind_rank ASC
        return (-urgency, -is_customer, kind_rank)

    resolved.sort(key=_trigger_sort_key)

    # ── Phase 3: Compose actions in ranked order ─────────────────────────────────
    actions = []
    for item in resolved:
        action = compose(item["category"], item["merchant"], item["trigger"], item["customer"])

        store.record_turn(
            action["conversation_id"],
            action["merchant_id"],
            action["customer_id"],
            action["send_as"],
            action["body"],
            {"trigger_id": item["trigger_id"], "cta": action["cta"]}
        )

        actions.append(action)

    return {"actions": actions}


def _load_trigger_from_seed(trigger_id: str) -> Optional[Dict]:
    """Load a trigger from the seed dataset file."""
    from pathlib import Path
    seed_file = Path("dataset/triggers_seed.json")
    if seed_file.exists():
        try:
            with open(seed_file) as f:
                s_data = json.load(f)
            t_list = s_data.get("triggers", [])
            return next((t for t in t_list if t.get("id") == trigger_id), None)
        except Exception:
            pass
    return None


def _load_merchant_from_seed(merchant_id: str) -> Optional[Dict]:
    """Load a merchant from the seed dataset file."""
    from pathlib import Path
    m_file = Path("dataset/merchants_seed.json")
    if m_file.exists():
        try:
            with open(m_file) as f:
                m_data = json.load(f)
            m_list = m_data.get("merchants", [])
            return next((m for m in m_list if m.get("merchant_id") == merchant_id), None)
        except Exception:
            pass
    return None


def _load_category_from_seed(cat_slug: str) -> Optional[Dict]:
    """Load a category from the dataset file."""
    from pathlib import Path
    c_file = Path(f"dataset/categories/{cat_slug}.json")
    if c_file.exists():
        try:
            with open(c_file) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _load_customer_from_seed(customer_id: str) -> Optional[Dict]:
    """Load a customer from the seed dataset file."""
    from pathlib import Path
    c_file = Path("dataset/customers_seed.json")
    if c_file.exists():
        try:
            with open(c_file) as f:
                c_data = json.load(f)
            c_list = c_data.get("customers", [])
            return next((c for c in c_list if c.get("customer_id") == customer_id), None)
        except Exception:
            pass
    return None


@app.post("/v1/reply")
async def reply_handler(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"accepted": False, "reason": "invalid_json"}
        )

    conv_id = data.get("conversation_id", f"conv_{uuid.uuid4().hex[:8]}")
    merchant_id = data.get("merchant_id", "m_unknown")
    customer_id = data.get("customer_id")
    from_role = data.get("from_role", "merchant")
    message = data.get("message", "")
    turn_number = data.get("turn_number", 1)

    result = handle_reply(conv_id, merchant_id, customer_id, from_role, message, turn_number)
    return result
