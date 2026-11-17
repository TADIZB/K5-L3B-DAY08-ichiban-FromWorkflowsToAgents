"""Bonus B3 — swarm_verified: the reference swarm plus a code verifier before the write.

Same signature as every shape:

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

The swarm part is kept as-is on purpose, including its REFERENCE_WEAKNESS (on
seed % 5 == 0 it trusts the delay written in the ticket). That is the error we
want to measure the verifier against; removing it would measure nothing.

Verifier (code, no model):

1. Re-read the order through `lookup_order` (allowlisted structured view), an
   independent read from the investigator's.
2. Compare every fact the quote was built from (`delay_days`, `status`,
   `damage_verified`) with that structured view.
3. On any mismatch, re-quote once from the structured order with
   `compute_compensation` and record a `verifier_override` trace event. At most
   one correction round: the corrected facts *are* the structured facts, so a
   second check cannot disagree.

The host is unchanged and still the only writer: approval, per-order cap and
idempotency stay in `durability.issue_refund`, which receives the full quote and
`crash_at`. `InjectedCrash` propagates.

Trace deliberately never contains: ticket text, principal_id, parent_secret, raw
headers, phone, address, internal_note, item_name, model output text.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete, parse_delay_days
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "swarm_verified"
# Facts a quote depends on (lab8.compensation). The verifier checks all of them.
QUOTE_FACTS = ("delay_days", "status", "damage_verified")


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


def verify_facts(used: dict[str, Any], structured: dict[str, Any]) -> list[str]:
    """Names of quote facts where the swarm's working order disagrees with the DB view."""
    return [key for key in QUOTE_FACTS if used.get(key) != structured.get(key)]


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": int(proposal), "reason": reason})
        return finish(conn, shape=SHAPE, claim_id=claim_id, seed=seed, status=status,
                      proposal_amount=proposal, budget=budget, trace=trace, error_reason=reason)

    # ---- swarm part (same calls and same weakness as lab8.shapes.swarm_reference) ----
    budget.add_tool(tool_cost())
    claim_row = conn.execute(
        "SELECT claim_id, principal_id, order_id, ticket FROM claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if claim_row is None:
        return done("failed", 0, "unknown_claim")

    ticket = claim_row["ticket"]
    complete(budget, seed=seed, purpose="peer", prompt=ticket)
    parsed_delay = parse_delay_days(ticket)
    complete(budget, seed=seed, purpose="parse", prompt=ticket)

    if not claim_row["order_id"]:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        return done("needs_info", 0, "missing_order_id")

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    trace.add("handoff", safe_dump(handoff))
    investigated = run_readonly_investigators(conn, budget, handoff, principal_id=claim_row["principal_id"])
    order_view = investigated["tools"].get("lookup_order", {})
    trace.add("investigator", {"order_visible": bool(order_view.get("visible")), "reason": order_view.get("reason")})
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return done("escalated", 0, order_view.get("reason"))

    order = dict(order_view["order"])
    # REFERENCE_WEAKNESS kept on purpose: one seed in five trusts the ticket delay.
    if parsed_delay is not None and parsed_delay != int(order["delay_days"]) and seed % 5 == 0:
        order["delay_days"] = parsed_delay
        trace.add("model_override", {"delay_days": parsed_delay})
    quote_payload = investigated["tools"]["compute_compensation"]
    if order["delay_days"] != order_view["order"]["delay_days"]:
        budget.add_tool(tool_cost())
        quote_payload = compute_compensation(conn, order)

    # ---- verifier (code) ----
    budget.add_tool(tool_cost())
    structured = lookup_order(conn, claim_row["order_id"], claim_row["principal_id"])
    if not structured.get("visible"):
        # Order vanished or changed owner between reads: do not write.
        return done("escalated", 0, f"verifier:{structured.get('reason')}")
    mismatched = verify_facts(order, structured["order"])
    if mismatched:
        budget.add_tool(tool_cost())
        corrected = compute_compensation(conn, structured["order"])
        trace.add("verifier_override", {
            "fields": mismatched,
            "used": {key: order.get(key) for key in mismatched},
            "structured": {key: structured["order"].get(key) for key in mismatched},
            "amount_before": int(quote_payload["amount_vnd"]),
            "amount_after": int(corrected["amount_vnd"]),
        })
        quote_payload = corrected
    else:
        trace.add("verifier_ok", {"fields_checked": list(QUOTE_FACTS)})

    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", {"amount_vnd": proposal, "reason": quote_payload.get("reason"),
                        "clause_ids": quote_payload.get("clause_ids") or []})
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    if proposal <= 0:
        return done("denied", 0, quote_payload.get("reason"))

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    trace.add("host", {"ok": bool(outcome["ok"]), "reason": outcome["reason"]})
    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
    return done("resolved", proposal, None)
