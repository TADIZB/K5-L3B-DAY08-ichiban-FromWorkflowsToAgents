"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.

Security boundary of this shape (what the trace deliberately never contains):

- claim row fields other than claim_id / order_id: no parent_secret, no raw headers,
  no principal_id, no ticket text (ticket is user data and may carry injection text);
- order PII: phone, address, internal_note, item_name. Only `ORDER_TRACE_FIELDS`
  (a subset of `lab8.tools.ORDER_FIELDS`) are copied from the investigator's order view;
- model output text. Only the purpose of each mock model call is recorded.

The handoff given to investigators is built only through `make_handoff` (allowlist +
canary check in `lab8.handoff.sanitize`) and carries read-only tools. The investigator
never receives a write tool; only the orchestrator calls `durability.issue_refund`.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import READONLY_TOOLS, WRITE_TOOLS, HandoffError, make_handoff
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"
INVESTIGATOR_TASK = "check_applicable_policy"
# compute_compensation is NOT handed to the investigator: money is decided by the
# orchestrator in code, from the investigator's order view.
INVESTIGATOR_TOOLS = ["lookup_order", "lookup_policy", "lookup_refund_history"]
# Order fields allowed in the trace. Never phone/address/internal_note/item_name.
ORDER_TRACE_FIELDS = (
    "order_id",
    "status",
    "delay_days",
    "shipping_fee_vnd",
    "paid_vnd",
    "damage_verified",
    "carrier",
)
# Last line of defence: if any of these reach a trace event, the event is replaced.
_TRACE_DENY_MARKERS = (
    "CANARY_",
    "parent_secret",
    "raw_headers",
    "Bearer ",
    "Authorization",
    "phone",
    "address",
    "internal_note",
    "item_name",
)


class _GuardedTrace:
    """Wraps lab8.trace.Trace. Every payload is copied and scanned before it is kept."""

    def __init__(self, run_id: str) -> None:
        self._inner = Trace(run_id)

    @property
    def run_id(self) -> str:
        return self._inner.run_id

    def add(self, kind: str, payload: dict[str, Any]) -> None:
        clean = safe_dump(payload)
        blob = json.dumps(clean, ensure_ascii=False)
        if any(marker in blob for marker in _TRACE_DENY_MARKERS):
            clean = {"redacted": True, "reason": "deny_marker_in_payload"}
        self._inner.add(kind, clean)

    def write(self) -> str:
        return self._inner.write()


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = _GuardedTrace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": int(proposal), "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,  # type: ignore[arg-type]  # same add/write/run_id surface as Trace
            error_reason=reason,
        )

    try:
        # 1. Orchestrator reads the claim through the allowlisted view (never SELECT *).
        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)
        if not claim.get("found"):
            return done("failed", 0, "unknown_claim")
        trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(claim.get("order_id"))})

        # The model only reads the ticket to plan; it never picks the amount or writes.
        complete(budget, seed=seed, purpose="plan", prompt=str(claim.get("ticket") or ""))

        if not claim.get("order_id"):
            complete(budget, seed=seed, purpose="draft", prompt="needs_info")
            return done("needs_info", 0, "missing_order_id")

        # 2. Sanitized handoff: allowlisted fields, read-only tools, no facts from the ticket.
        handoff = make_handoff(
            request_id=f"REQ-{claim_id}-s{seed}",
            claim_id=claim_id,
            task=INVESTIGATOR_TASK,
            facts={},
            allowed_tools=list(INVESTIGATOR_TOOLS),
        )
        _assert_readonly(handoff)
        trace.add("handoff", handoff)

        investigated = run_readonly_investigators(
            conn, budget, handoff, principal_id=str(claim["principal_id"])
        )
        tools = investigated.get("tools") or {}
        order_view = tools.get("lookup_order") or {}
        history = tools.get("lookup_refund_history") or {}
        policy_count = len((tools.get("lookup_policy") or {}).get("policies") or [])

        if not order_view.get("visible"):
            trace.add("investigator", {"order_visible": False, "reason": order_view.get("reason")})
            complete(budget, seed=seed, purpose="draft", prompt="escalated")
            return done("escalated", 0, order_view.get("reason") or "order_not_visible")

        order = {key: order_view["order"][key] for key in ORDER_TRACE_FIELDS}
        trace.add(
            "investigator",
            {
                "order_visible": True,
                "order": order,
                "policy_count": policy_count,
                "prior_refunded_vnd": int(history.get("refunded_vnd") or 0),
            },
        )

        # 3. Money stays in code: quote from the DB order view, ignore ticket delay numbers.
        budget.add_tool(tool_cost())
        quote = compute_compensation(conn, order)
        proposal = int(quote["amount_vnd"])
        trace.add(
            "quote",
            {"amount_vnd": proposal, "reason": quote.get("reason"), "clause_ids": quote.get("clause_ids") or []},
        )

        if proposal <= 0:
            complete(budget, seed=seed, purpose="draft", prompt="denied")
            return done("denied", 0, quote.get("reason") or "zero_quote")

        # 4. Only the orchestrator writes. Full quote; the host caps by order and approval.
        try:
            outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except InjectedCrash:
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise
        trace.add("host", {"ok": bool(outcome["ok"]), "reason": outcome["reason"]})

        complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
        if not outcome["ok"]:
            status = "failed" if outcome.get("conflict") else "denied"
            return done(status, proposal, outcome["reason"])
        return done("resolved", proposal, None)
    except InjectedCrash:
        raise
    except (HandoffError, ToolRejected) as exc:
        return done("failed", 0, f"security_guard:{type(exc).__name__}")
    except (sqlite3.Error, KeyError, TypeError, ValueError) as exc:
        return done("failed", 0, f"internal_error:{type(exc).__name__}")


def _assert_readonly(handoff: dict[str, Any]) -> None:
    tools = set(handoff.get("allowed_tools") or [])
    if tools & WRITE_TOOLS or not tools <= READONLY_TOOLS:
        raise HandoffError("investigator handoff must carry read-only tools only")
