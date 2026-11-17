"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8 import durability
from lab8.db import connect
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace


MAX_REACT_STEPS = 8


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
        # Also release the database when InjectedCrash propagates to the caller.
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))

    def done(status: str, proposal: int = 0, reason: str | None = None) -> RunResult:
        # No ticket, tool output, identifiers or parent context enter this prompt.
        complete(budget, seed=seed, purpose="draft", prompt=f"status={status};proposal={proposal}")
        trace.add("decision", {"status": status, "reason": reason})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add("claim", {"found": claim["found"], "has_order": bool(claim.get("order_id"))})
    if not claim["found"]:
        return done("failed", reason="unknown_claim")

    # Keep ticket text out of the loop: user prose cannot supply identity or facts.
    claim_context = {key: claim[key] for key in ("claim_id", "principal_id", "order_id")}
    evidence: dict[str, dict[str, Any]] = {}
    decision_steps = 0

    def decide(observation: dict[str, Any]) -> dict[str, Any]:
        nonlocal decision_steps
        last_tool = observation.get("last_tool")
        if last_tool in ("lookup_order", "lookup_policy", "lookup_refund_history"):
            evidence[last_tool] = observation["last_result"]

        order_view = evidence.get("lookup_order")
        scope_args = {
            "order_id": claim_context["order_id"],
            "principal_id": claim_context["principal_id"],
        }
        if not claim_context["order_id"]:
            action: dict[str, Any] = {"final": {}}
        elif order_view is None:
            action = {"tool": "lookup_order", "args": scope_args}
        elif not order_view["visible"]:
            action = {"final": {}}
        elif "lookup_policy" not in evidence:
            action = {"tool": "lookup_policy", "args": {}}
        elif "lookup_refund_history" not in evidence:
            action = {"tool": "lookup_refund_history", "args": scope_args}
        else:
            action = {"final": {}}

        decision_steps += 1
        action_name = action.get("tool", "final")
        # MockLLM emits opaque text, not structured tool calls. The lab's decision
        # policy therefore maps observations to read actions in code. Record every
        # simulated decision call, but never execute or parse its text as a command.
        complete(
            budget,
            seed=seed,
            purpose="decide",
            prompt=f"read_only_review;step={decision_steps};last={last_tool};action={action_name}",
        )
        trace.add("react", {"step": decision_steps, "action": action_name})
        return action

    try:
        investigation = run_react(
            conn,
            budget,
            observation={"claim": claim_context},
            decide=decide,
            max_steps=MAX_REACT_STEPS,
            worker=True,
        )
    except ToolRejected:
        return done("failed", reason="tool_rejected")

    if investigation["stopped"] != "final":
        return done("failed", reason="step_cap")
    if not claim_context["order_id"]:
        return done("needs_info", reason="missing_order_id")
    order_view = evidence.get("lookup_order")
    if order_view is None:
        return done("failed", reason="incomplete_investigation")
    if not order_view["visible"]:
        return done("escalated", reason=order_view["reason"])
    if "lookup_policy" not in evidence or "lookup_refund_history" not in evidence:
        return done("failed", reason="incomplete_investigation")

    # The final model payload has no authority over the quote or the write.
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    proposal = int(quote["amount_vnd"])
    trace.add("quote", quote)
    if proposal <= 0:
        return done("denied", reason=quote["reason"])

    # Full entitlement goes to the host; it owns approval, caps and idempotency.
    # Do not catch InjectedCrash: the caller must observe the actual crash window.
    outcome = durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    trace.add("host_refund", {"ok": outcome["ok"], "reason": outcome["reason"]})
    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
    return done("resolved", proposal)
