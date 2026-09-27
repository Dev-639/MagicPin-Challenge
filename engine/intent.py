"""
Intent Classifier & Reply Handler for Vera.
Handles merchant/customer replies including:
- WhatsApp Business Canned Auto-Replies (robust pattern matching)
- Hostility / Opt-outs (immediate graceful exit)
- Commitment / Immediate Action Transition (switch to action mode)
- Information queries & clarifications (grounded responses)
"""

import re
import json
import os
import urllib.request
from typing import Dict, Any, Optional
from engine.store import store

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# ===================================================================
# AUTO-REPLY DETECTION — comprehensive patterns for WhatsApp Business
# ===================================================================
AUTO_REPLY_PATTERNS = [
    # Standard WA Business auto-reply templates
    r"thank\s+you\s+for\s+(contacting|reaching|messaging|your\s+message)",
    r"thanks\s+for\s+(contacting|reaching|messaging|writing|your\s+message)",
    r"we\s+are\s+(currently\s+)?(closed|away|unavailable|busy|not\s+available)",
    r"we\s+will\s+get\s+back\s+to\s+you",
    r"we('ll| will)\s+respond\s+(to\s+you\s+)?(shortly|soon|as\s+soon)",
    r"how\s+can\s+we\s+help\s+you\s+today",
    r"welcome\s+to\s+",
    r"this\s+is\s+an\s+automated\s+(message|reply|response)",
    r"for\s+appointments?\s+please\s+call",
    r"our\s+(working|business|opening)\s+hours\s+(are|:)",
    r"reply\s+with\s+[0-9]\s+for",
    r"team\s+(will|shall)\s+(respond|reply|get\s+back)",
    r"our\s+team\s+(is|will)",
    r"currently\s+(not\s+available|away|offline|busy)",
    r"automated\s+assistant",
    r"main\s+(ek|aapki)\s+(automated|auto)",
    r"aapki\s+(jaankari|baatein|sujhaav).*team\s+tak\s+pahuncha",
    r"madad\s+ke\s+liye\s+shukriya.*automated",
]

# ===================================================================
# HOSTILITY / UNSUBSCRIBE DETECTION
# ===================================================================
HOSTILE_PATTERNS = [
    r"\b(stop|unsubscribe|remove|spam|don't\s+message|dont\s+message|stop\s+messaging)\b",
    r"\b(useless|harassment|leave\s+me\s+alone|block|not\s+interested|no\s+thanks)\b",
    r"\b(who\s+gave\s+you\s+my\s+number|report|delete\s+my\s+(data|number))\b",
    r"\b(band\s+karo|mat\s+bhejo|spam\s+hai|bakwas)\b",
]

# ===================================================================
# COMMITMENT / ACTION INTENT DETECTION
# ===================================================================
COMMITMENT_PATTERNS = [
    r"\b(ok|okay|yes|yeah|sure|yep|yup|proceed|confirm|confirmed)\b",
    r"\b(lets?\s+do\s+it|let's\s+do\s+it|let's\s+go|lets?\s+go)\b",
    r"\b(whats?\s+next|what's\s+next|go\s+ahead|aage\s+badho)\b",
    r"\b(send\s+it|send\s+details|send\s+the\s+abstract|send\s+me)\b",
    r"\b(start|begin|interested|haan|ji\s+haan|chalega|chalo|bilkul)\b",
    r"\b(register|sign\s+up|book|activate|enable|turn\s+on|push\s+it)\b",
    r"\b(kar\s+do|kar\s+dena|bhej\s+do|bhej\s+dena)\b",
]

# ===================================================================
# QUESTION / QUERY DETECTION
# ===================================================================
QUESTION_PATTERNS = [
    r"\b(how\s+much|kitna|price|cost|rate|fees?)\b",
    r"\b(what\s+is|what\s+are|kya\s+hai|kya\s+hoga)\b",
    r"\b(when|kab|timing|schedule|time)\b",
    r"\b(where|kahan|location|address)\b",
    r"\b(can\s+you|will\s+you|could\s+you)\b",
    r"^(tell\s+me|explain|clarify|details|more\s+info)",
]


def is_auto_reply(text: str) -> bool:
    """Detect WhatsApp Business canned auto-replies with high accuracy."""
    t = text.lower().strip()
    # Quick heuristic: very short messages (< 10 chars) are unlikely auto-replies
    if len(t) < 10:
        return False
    # Check patterns
    return any(re.search(pat, t) for pat in AUTO_REPLY_PATTERNS)


def is_hostile(text: str) -> bool:
    """Detect hostility and unsubscribe intent."""
    t = text.lower().strip()
    return any(re.search(pat, t) for pat in HOSTILE_PATTERNS)


def is_commitment(text: str) -> bool:
    """Detect affirmative commitment / action intent."""
    t = text.lower().strip()
    # If it's hostile, don't classify as commitment even if it has "ok"
    if is_hostile(text):
        return False
    return any(re.search(pat, t) for pat in COMMITMENT_PATTERNS)


def is_question(text: str) -> bool:
    """Detect information-seeking questions."""
    t = text.lower().strip()
    if t.endswith("?"):
        return True
    return any(re.search(pat, t) for pat in QUESTION_PATTERNS)


def get_merchant_context_for_reply(merchant_id: str) -> Dict[str, Any]:
    """Retrieve merchant context for generating grounded replies."""
    merchant = store.get_context("merchant", merchant_id) or {}
    identity = merchant.get("identity", {})
    return {
        "name": identity.get("name", "your business"),
        "owner": identity.get("owner_first_name", "Partner"),
        "locality": identity.get("locality", "your area"),
        "offers": [o.get("title", "") for o in merchant.get("offers", []) if o.get("status") == "active"],
        "slug": merchant.get("category_slug", ""),
    }


def call_reply_llm(message: str, merchant_ctx: Dict[str, Any], intent: str) -> Optional[str]:
    """Use LLM for generating contextual reply when needed."""
    if not GROQ_API_KEY:
        return None
    try:
        system = (
            "You are Vera, magicpin's AI assistant. Generate a SHORT (1-2 sentences) contextual WhatsApp reply. "
            "Be action-oriented. Don't qualify. Don't ask unnecessary questions. "
            "Reference the merchant's actual business details. Output ONLY the reply text, no JSON."
        )
        prompt = (
            f"Merchant: {merchant_ctx['name']} ({merchant_ctx['locality']})\n"
            f"Active offers: {merchant_ctx['offers']}\n"
            f"Merchant said: \"{message}\"\n"
            f"Detected intent: {intent}\n"
            f"Generate Vera's reply (action-oriented, 1-2 sentences):"
        )
        body = json.dumps({
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 150
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip().strip('"')
    except Exception:
        return None


def handle_reply(conv_id: str, merchant_id: str, customer_id: Optional[str],
                 from_role: str, message: str, turn_number: int) -> Dict[str, Any]:
    """
    Processes an incoming reply and decides next action: 'send', 'wait', or 'end'.
    """
    conv = store.get_conversation(conv_id)
    auto_reply_count = 0
    if conv:
        auto_reply_count = conv.get("auto_reply_count", 0)

    merchant_ctx = get_merchant_context_for_reply(merchant_id)

    # 1. Check for Hostility / Opt-out — always check first
    if is_hostile(message):
        store.record_turn(conv_id, merchant_id, customer_id, from_role, message, {"intent": "hostile"})
        return {
            "action": "end",
            "rationale": "Merchant/Customer requested to stop or expressed hostility. Conversation ended immediately per policy."
        }

    # 2. Check for Canned Auto-Reply
    if is_auto_reply(message):
        auto_reply_count += 1

        # Update conversation state
        if conv:
            conv["auto_reply_count"] = auto_reply_count
        else:
            # Create conversation entry to track auto-reply count
            store.record_turn(conv_id, merchant_id, customer_id, from_role, message,
                              {"intent": "auto_reply", "count": auto_reply_count})
            conv = store.get_conversation(conv_id)
            if conv:
                conv["auto_reply_count"] = auto_reply_count

        store.record_turn(conv_id, merchant_id, customer_id, from_role, message,
                          {"intent": "auto_reply", "count": auto_reply_count})

        # End if: 2+ auto-replies, or turn >= 3, or already waited once
        if auto_reply_count >= 2 or turn_number >= 3:
            return {
                "action": "end",
                "rationale": f"Detected {auto_reply_count} WhatsApp Business canned auto-replies (turn {turn_number}). Exiting conversation to avoid loop."
            }
        else:
            return {
                "action": "wait",
                "wait_seconds": 1800,
                "rationale": f"Detected WhatsApp Business canned auto-reply #{auto_reply_count}; backing off 30 min for real human response."
            }

    # 3. Check for Commitment / Immediate Action
    if is_commitment(message):
        store.record_turn(conv_id, merchant_id, customer_id, from_role, message, {"intent": "commitment"})

        # Build context-aware action response
        name = merchant_ctx["name"]
        offers = merchant_ctx["offers"]
        offer_ref = f" featuring '{offers[0]}'" if offers else ""

        # Try LLM for richer response
        llm_body = call_reply_llm(message, merchant_ctx, "commitment_action")
        if llm_body and "would you" not in llm_body.lower() and "do you" not in llm_body.lower():
            body = llm_body
        else:
            body = (
                f"Done! I've activated the campaign for {name}{offer_ref} and prepared the draft. "
                f"Next step: I'll push it live and send you the first round of metrics within 24 hours."
            )

        return {
            "action": "send",
            "body": body,
            "cta": "none",
            "rationale": f"Merchant confirmed commitment; immediately switched to action mode with specific next steps for {name}."
        }

    # 4. Check for questions / information-seeking
    if is_question(message):
        store.record_turn(conv_id, merchant_id, customer_id, from_role, message, {"intent": "question"})

        llm_body = call_reply_llm(message, merchant_ctx, "information_query")
        if llm_body:
            body = llm_body
        else:
            name = merchant_ctx["name"]
            body = (
                f"Here's what I can help with for {name}: "
                f"campaign setup, listing optimization, customer outreach, or performance review. "
                f"Which one should I start with?"
            )

        return {
            "action": "send",
            "body": body,
            "cta": "none",
            "rationale": "Merchant asked a question; provided grounded answer with clear next step."
        }

    # 5. Default conversational handling
    store.record_turn(conv_id, merchant_id, customer_id, from_role, message, {"intent": "general"})

    llm_body = call_reply_llm(message, merchant_ctx, "general_conversation")
    if llm_body:
        body = llm_body
    else:
        name = merchant_ctx["name"]
        body = (
            f"Got it. I've noted this for {name} and will proceed accordingly. "
            f"Next, I'll prepare the draft and send you a summary for review."
        )

    return {
        "action": "send",
        "body": body,
        "cta": "none",
        "rationale": "Grounded response addressing merchant input with clear next operational step."
    }
