"""
In-memory thread-safe state store for categories, merchants, customers, triggers, and conversations.
Supports idempotent version updates, conflict detection, suppression key tracking,
and cross-conversation auto-reply tracking per merchant.
"""

import threading
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone


class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        # scope -> context_id -> {"version": int, "payload": dict, "stored_at": str}
        self._storage: Dict[str, Dict[str, Dict[str, Any]]] = {
            "category": {},
            "merchant": {},
            "customer": {},
            "trigger": {}
        }
        # suppression_key -> datetime of expiry or creation
        self._suppressions: Dict[str, str] = {}
        # conversation_id -> conversation state dict
        self._conversations: Dict[str, Dict[str, Any]] = {}
        # merchant_id -> auto-reply count (tracks across all conversations)
        self._merchant_auto_reply_count: Dict[str, int] = {}
        self._start_time = datetime.now(timezone.utc)

    def get_uptime_seconds(self) -> int:
        return int((datetime.now(timezone.utc) - self._start_time).total_seconds())

    def save_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Saves context.
        Returns: (accepted: bool, error_reason: Optional[str], current_version: Optional[int])
        """
        with self._lock:
            if scope not in self._storage:
                return False, "invalid_scope", None

            existing = self._storage[scope].get(context_id)
            if existing is not None:
                current_version = existing["version"]
                if version == current_version:
                    # Idempotent re-post of same version is 200 OK no-op
                    return True, None, current_version
                elif version < current_version:
                    # Stale version conflict
                    return False, "stale_version", current_version

            now_str = datetime.now(timezone.utc).isoformat()
            self._storage[scope][context_id] = {
                "version": version,
                "payload": payload,
                "stored_at": now_str
            }
            if scope == "trigger":
                sup_key = payload.get("suppression_key")
                if sup_key and sup_key in self._suppressions:
                    del self._suppressions[sup_key]
            return True, None, version

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._storage.get(scope, {}).get(context_id)
            return record["payload"] if record else None

    def get_all(self, scope: str) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {cid: rec["payload"] for cid, rec in self._storage.get(scope, {}).items()}

    def is_suppressed(self, suppression_key: Optional[str]) -> bool:
        if not suppression_key:
            return False
        with self._lock:
            return suppression_key in self._suppressions

    def set_suppression(self, suppression_key: Optional[str], expires_at: Optional[str] = None):
        if not suppression_key:
            return
        with self._lock:
            self._suppressions[suppression_key] = expires_at or datetime.now(timezone.utc).isoformat()

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._conversations.get(conv_id)

    def record_turn(self, conv_id: str, merchant_id: str, customer_id: Optional[str], role: str, message: str, meta: Optional[Dict] = None):
        with self._lock:
            if conv_id not in self._conversations:
                self._conversations[conv_id] = {
                    "conversation_id": conv_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer_id,
                    "turns": [],
                    "auto_reply_count": 0,
                    "state": "active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            self._conversations[conv_id]["turns"].append({
                "role": role,
                "message": message,
                "meta": meta or {},
                "ts": datetime.now(timezone.utc).isoformat()
            })

    def get_merchant_auto_reply_count(self, merchant_id: str) -> int:
        """Get total auto-reply count across all conversations for a merchant."""
        with self._lock:
            return self._merchant_auto_reply_count.get(merchant_id, 0)

    def increment_merchant_auto_reply(self, merchant_id: str) -> int:
        """Increment and return auto-reply count for a merchant."""
        with self._lock:
            count = self._merchant_auto_reply_count.get(merchant_id, 0) + 1
            self._merchant_auto_reply_count[merchant_id] = count
            return count

    def reset_merchant_auto_reply(self, merchant_id: str):
        """Reset auto-reply count when a real message is received."""
        with self._lock:
            self._merchant_auto_reply_count[merchant_id] = 0


# Global singleton instance
store = ContextStore()
