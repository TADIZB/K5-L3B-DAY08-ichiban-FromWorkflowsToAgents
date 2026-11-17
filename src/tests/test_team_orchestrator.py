"""Team tests for shape C (orchestrator): handoff security, trace hygiene, retry and crash.

Owner: Người 3 (Orchestrator và bảo mật handoff).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lab8 import runtime
from lab8.db import connect, init_store
from lab8.durability import InjectedCrash
from lab8.handoff import ALLOWED_FIELDS, FACT_KEYS, READONLY_TOOLS, WRITE_TOOLS
from lab8.metrics import trial_pass
from lab8.shapes import orchestrator
from tests.conftest import BY_ID, CLAIMS, WORLD

ALL_CLAIM_IDS = [row["claim_id"] for row in CLAIMS]
ORDER_PII_KEYS = ("phone", "address", "internal_note", "item_name")


def _store(tmp_path: Path, name: str = "orch.sqlite") -> str:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _all_pii_values() -> list[str]:
    values = []
    for order in WORLD["orders"]:
        values.extend(str(order[key]) for key in ORDER_PII_KEYS)
    return values


def _secrets_for(claim_id: str) -> list[str]:
    row = BY_ID[claim_id]
    return [row["parent_secret"], json.dumps(row["raw_headers"]), *row["raw_headers"].values()]


@pytest.fixture
def captured_handoffs(monkeypatch):
    """Record exactly what the orchestrator hands to the investigator runner."""
    seen: list[dict] = []
    real = runtime.run_readonly_investigators

    def spy(conn, budget, handoff, principal_id):
        seen.append(json.loads(json.dumps(handoff)))
        return real(conn, budget, handoff, principal_id=principal_id)

    monkeypatch.setattr(orchestrator, "run_readonly_investigators", spy)
    return seen


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_handoff_is_allowlisted_and_has_no_secret(tmp_path, captured_handoffs, claim_id):
    orchestrator.run_claim(claim_id, seed=11, store_path=_store(tmp_path))
    row = BY_ID[claim_id]
    if not row["order_id"]:
        assert captured_handoffs == [], "no investigator should run when order_id is missing"
        return
    assert len(captured_handoffs) == 1
    handoff = captured_handoffs[0]
    blob = json.dumps(handoff, ensure_ascii=False)
    assert set(handoff) <= ALLOWED_FIELDS
    assert set(handoff["facts"]) <= FACT_KEYS
    for key in ("parent_secret", "raw_headers", "ticket", "principal_id", "history", "order"):
        assert key not in handoff and key not in handoff["facts"]
    for forbidden in ("parent_secret", "raw_headers", "Bearer", "CANARY_"):
        assert forbidden not in blob
    for secret in _secrets_for(claim_id):
        assert secret not in blob
    # Ticket text is user data and is never forwarded to the investigator.
    assert row["ticket"] not in blob


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_investigator_never_gets_a_write_tool(tmp_path, captured_handoffs, claim_id):
    orchestrator.run_claim(claim_id, seed=22, store_path=_store(tmp_path))
    for handoff in captured_handoffs:
        tools = set(handoff["allowed_tools"])
        assert tools <= READONLY_TOOLS
        assert not tools & WRITE_TOOLS
        # Money is decided by the orchestrator, not delegated.
        assert "compute_compensation" not in tools


def test_investigator_dispatch_rejects_writes_even_if_handoff_is_tampered(public_db):
    from lab8.schemas import Budget

    conn = connect(public_db)
    try:
        tampered = {"claim_id": "C-001", "allowed_tools": ["issue_refund"]}
        with pytest.raises(runtime.ToolRejected):
            runtime.run_readonly_investigators(conn, Budget(), tampered, principal_id="P-100")
        assert conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id='C-001'").fetchone()["n"] == 0
    finally:
        conn.close()


def test_write_tool_in_handoff_turns_into_failed_not_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "INVESTIGATOR_TOOLS", ["lookup_order", "issue_refund"])
    store = _store(tmp_path)
    result = orchestrator.run_claim("C-001", seed=11, store_path=store)
    assert result.status == "failed"
    assert result.error_reason == "security_guard:HandoffError"
    assert result.refund_effects == []
    assert Path(result.trace_path).is_file()


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
@pytest.mark.parametrize("seed", [11, 55])
def test_trace_and_stdout_hold_no_secret_or_pii(tmp_path, capsys, claim_id, seed):
    result = orchestrator.run_claim(claim_id, seed=seed, store_path=_store(tmp_path))
    out = capsys.readouterr()
    body = Path(result.trace_path).read_text(encoding="utf-8")
    trace = json.loads(body)
    assert trace["run_id"] == result.run_id and isinstance(trace["events"], list)
    everything = body + out.out + out.err + json.dumps(result.as_dict(), ensure_ascii=False)
    for token in _secrets_for(claim_id) + _all_pii_values() + ["CANARY_"]:
        assert token not in everything, token
    for key in ORDER_PII_KEYS + ("parent_secret", "raw_headers", "ticket"):
        assert f'"{key}"' not in body


def test_trace_records_sanitized_handoff(tmp_path):
    result = orchestrator.run_claim("C-010", seed=11, store_path=_store(tmp_path))
    events = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))["events"]
    handoffs = [event["payload"] for event in events if event["kind"] == "handoff"]
    assert len(handoffs) == 1
    assert set(handoffs[0]) <= ALLOWED_FIELDS
    assert handoffs[0]["contract_version"] == "handoff.v1"


def test_guarded_trace_redacts_leaked_payload():
    guarded = orchestrator._GuardedTrace("R-orchestrator-test-s0")
    guarded.add("debug", {"parent_secret": "CANARY_SECRET_PARENT_X"})
    guarded.add("debug", {"order": {"phone": "0901000107"}})
    dumped = guarded._inner.dump()
    assert "CANARY_" not in dumped and "0901000107" not in dumped
    assert dumped.count("deny_marker_in_payload") == 2


@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
def test_ticket_delay_is_ignored_every_seed(tmp_path, seed):
    # C-002: ticket claims 5 days late, order row says 2 -> must deny on every seed.
    result = orchestrator.run_claim("C-002", seed=seed, store_path=_store(tmp_path))
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert result.refund_effects == []


def test_only_orchestrator_calls_issue_refund_once(tmp_path, monkeypatch):
    calls = []
    real = orchestrator.issue_refund

    def spy(conn, claim_id, proposed_vnd, *, crash_at=None):
        calls.append((claim_id, proposed_vnd, crash_at))
        return real(conn, claim_id, proposed_vnd, crash_at=crash_at)

    monkeypatch.setattr(orchestrator, "issue_refund", spy)
    result = orchestrator.run_claim("C-008", seed=11, store_path=_store(tmp_path))
    # Full quote is passed; the host caps the committed amount.
    assert calls == [("C-008", 35000, None)]
    assert result.status == "resolved" and result.proposal_amount == 35000
    assert result.refund_effects[0]["amount_vnd"] == 20000


def test_unknown_claim_fails_with_trace(tmp_path):
    result = orchestrator.run_claim("C-999", seed=11, store_path=_store(tmp_path))
    assert result.status == "failed" and result.error_reason == "unknown_claim"
    assert json.loads(Path(result.trace_path).read_text(encoding="utf-8"))["run_id"] == result.run_id


def test_retry_keeps_one_refund(tmp_path):
    store = _store(tmp_path)
    first = orchestrator.run_claim("C-011", seed=11, store_path=store)
    second = orchestrator.run_claim("C-011", seed=11, store_path=store)
    assert first.status == second.status == "resolved"
    conn = connect(store)
    try:
        rows = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id='C-011'").fetchone()["n"]
    finally:
        conn.close()
    assert rows == 1 and second.committed_audit_count == 1


def test_amount_conflict_is_failed_and_keeps_committed_row(tmp_path):
    store = _store(tmp_path)
    orchestrator.run_claim("C-001", seed=11, store_path=store)
    conn = connect(store)
    conn.execute("UPDATE refund_ledger SET amount_vnd = 1000 WHERE claim_id = 'C-001'")
    conn.commit()
    conn.close()
    result = orchestrator.run_claim("C-001", seed=11, store_path=store)
    assert result.status == "failed" and result.error_reason == "amount_conflict"
    assert result.refund_effects[0]["amount_vnd"] == 1000


@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_crash_propagates_then_resume_pays_once(tmp_path, crash_at):
    store = _store(tmp_path)
    with pytest.raises(InjectedCrash):
        orchestrator.run_claim("C-012", seed=11, store_path=store, crash_at=crash_at)
    # The crash path still flushes a valid trace without secrets.
    crash_trace = Path("traces") / "R-orchestrator-C-012-s11.json"
    body = json.loads(crash_trace.read_text(encoding="utf-8"))
    assert body["events"][-1] == {"kind": "crash", "payload": {"at": crash_at}}
    assert "CANARY_" not in json.dumps(body)

    started_at = time.time()
    result = orchestrator.run_claim("C-012", seed=11, store_path=store)
    conn = connect(store)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID["C-012"]["expected"], conn, started_at=started_at)
        rows = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id='C-012'").fetchone()["n"]
    finally:
        conn.close()
    assert passed, reason
    assert rows == 1
