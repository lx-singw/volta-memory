"""Fast, database-free checks for the product-facing memory contract."""

from app.api.contracts import (
    EndSessionResponseDTO,
    MemoryChangeDTO,
    ProfileFactDTO,
    ProfileResponseDTO,
    PublicMemorySnapshotDTO,
)
from app.memory.provenance import sanitize_provenance
import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4


def test_source_quote_is_only_verified_against_the_claimed_user_turn():
    evidence, slot = sanitize_provenance(
        {
            "source_quote": "Actually, my bill is R3,800.",
            "source_turn_index": 3,
            "profile_slot": "monthly_bill",
            "is_constraint": False,
        },
        [
            {"message_id": "first", "turn_index": 1, "content": "Hello."},
            {"message_id": "third", "turn_index": 3, "content": "Actually, my bill is R3,800."},
        ],
        "User has a monthly bill of R3,800",
    )

    assert evidence["source_verified"] is True
    assert evidence["source_quote"] == "Actually, my bill is R3,800."
    assert evidence["source_message_id"] == "third"
    assert slot.value == "monthly_bill"


def test_bad_model_quote_is_not_exposed_as_evidence():
    evidence, _slot = sanitize_provenance(
        {"source_quote": "A fabricated quote", "source_turn_index": 1},
        [{"message_id": "one", "turn_index": 1, "content": "Real user message"}],
        "User prefers backup power",
    )

    assert evidence["source_verified"] is False
    assert evidence["source_quote"] is None
    assert evidence["source_turn_index"] is None
    assert evidence["source_message_id"] is None


def test_camel_case_receipt_and_profile_contracts_are_stable():
    snapshot = PublicMemorySnapshotDTO(
        id="new",
        observation="User has a monthly bill of R3,800",
        memory_type="correction",
        profile_slot="monthly_bill",
        confidence=0.95,
    )
    receipt = EndSessionResponseDTO(
        session_id="session",
        ended_at="2026-07-20T00:00:00+00:00",
        memory_changes=[MemoryChangeDTO(action="corrected", after=snapshot)],
    ).model_dump(by_alias=True)
    profile = ProfileResponseDTO(
        entity_id="entity",
        current_fact_count=1,
        retained_fact_count=1,
        last_confirmed_at="2026-07-20T00:00:00+00:00",
        facts=[
            ProfileFactDTO(
                profile_slot="monthly_bill",
                label="Electricity bill",
                display_value="R3,800",
                status="eligible",
                source_memory_id="new",
                confidence=0.95,
            )
        ],
    ).model_dump(by_alias=True)

    assert receipt["memoryChanges"][0]["action"] == "corrected"
    assert receipt["memoryChanges"][0]["after"]["profileSlot"] == "monthly_bill"
    assert profile["currentFactCount"] == 1
    assert profile["facts"][0]["displayValue"] == "R3,800"


def test_connection_context_forwards_errors_so_psycopg_can_rollback(monkeypatch):
    from app import db

    class FakeConnectionContext:
        def __init__(self):
            self.exit_args = None

        def __enter__(self):
            return object()

        def __exit__(self, *args):
            self.exit_args = args

    context = FakeConnectionContext()

    class FakePool:
        def connection(self):
            return context

    monkeypatch.setattr(db, "get_pool", lambda: FakePool())
    with pytest.raises(RuntimeError, match="boom"):
        with db.get_connection():
            raise RuntimeError("boom")

    assert context.exit_args[0] is RuntimeError


def test_any_read_only_workspace_is_blocked_from_mutation():
    from app.api.routes_v1 import _require_writable
    from app.auth import Workspace
    from fastapi import HTTPException

    workspace = Workspace(
        entity_id="immutable-demo",
        entity_type="anonymous",
        is_read_only=True,
        user_id=None,
        csrf_token="csrf",
        csrf_hash="hash",
    )
    with pytest.raises(HTTPException) as raised:
        _require_writable(workspace)

    assert raised.value.status_code == 403


def test_reinforcement_creates_a_versioned_relation_with_verified_new_provenance(monkeypatch):
    from app.chat import session
    from app.memory.models import Memory, MemoryDraft, MemoryType, ProfileSlot

    old = Memory(
        id=uuid4(),
        entity_id="entity",
        memory_type=MemoryType.PREFERENCE,
        observation="Keeping the lights on is the priority",
        base_confidence=0.9,
        reinforcement_count=2,
        cross_session_reinforcement_count=2,
        profile_slot=ProfileSlot.BACKUP_PRIORITY,
    )
    draft = MemoryDraft(
        memory_type=MemoryType.PREFERENCE,
        observation="Keeping lights on remains the priority",
        base_confidence=0.9,
        evidence={
            "source_quote": "Keeping the lights on is still my priority.",
            "source_turn_index": 3,
            "source_verified": True,
            "source_message_id": str(uuid4()),
        },
        profile_slot=ProfileSlot.BACKUP_PRIORITY,
    )
    new = old.model_copy(deep=True)
    new.id = uuid4()
    new.observation = draft.observation
    calls: dict[str, object] = {}

    updated = old.model_copy(deep=True)
    updated.reinforcement_count = 3
    updated.cross_session_reinforcement_count = 3
    updated.base_confidence = 0.93
    updated.last_reinforced_at = datetime.now(timezone.utc)

    monkeypatch.setattr("app.memory.decay.reinforce", lambda *_args, **_kwargs: updated)
    monkeypatch.setattr(session, "write_from_draft", lambda *_args, **_kwargs: new)
    monkeypatch.setattr(session, "update_memory_reinforcement", lambda **kwargs: calls.setdefault("update", kwargs))
    monkeypatch.setattr(session, "persist_provenance", lambda *_args: calls.setdefault("provenance", True))
    monkeypatch.setattr(session, "persist_relation", lambda _conn, source, target, relation, _sid: calls.setdefault("relation", (source, target, relation)))
    monkeypatch.setattr("app.memory.store.supersede", lambda source, target, **_kwargs: calls.setdefault("supersede", (source, target.id)))

    result = session._write_reinforcement_version(
        object(), target=old, draft=draft, entity_id="entity", session_id=uuid4()
    )

    assert result.id == new.id
    assert calls["relation"] == (old.id, new.id, "reinforces")
    assert calls["supersede"] == (old.id, new.id)
    assert calls["provenance"] is True
    assert calls["update"]["memory_id"] == new.id


def test_reinforcement_lifecycle_event_points_to_the_new_active_version(monkeypatch):
    from app.chat import session
    from app.memory.models import Memory, MemoryType, ProfileSlot

    predecessor = Memory(
        id=uuid4(), entity_id="entity", memory_type=MemoryType.PREFERENCE,
        observation="Keep the lights on", base_confidence=0.9,
        profile_slot=ProfileSlot.BACKUP_PRIORITY,
    )
    replacement = predecessor.model_copy(deep=True)
    replacement.id = uuid4()
    recorded: dict[str, object] = {}
    monkeypatch.setattr(session, "persist_lifecycle_event", lambda _conn, **kwargs: recorded.update(kwargs))

    session._persist_reinforcement_lifecycle_event(
        object(), entity_id="entity", session_id=uuid4(), target=predecessor,
        updated=replacement, change={"operation": "reinforced"},
    )

    assert recorded["before_memory_id"] == predecessor.id
    assert recorded["after_memory_id"] == replacement.id
    assert recorded["after_memory_id"] != predecessor.id


def test_exclusion_trace_reports_real_retrieval_reasons(monkeypatch):
    from app.chat import session
    from app.memory.models import Memory, MemoryType, ProfileSlot

    superseded = Memory(
        id=uuid4(), entity_id="entity", memory_type=MemoryType.FACT,
        observation="Monthly bill was R3,200", base_confidence=0.95,
        is_superseded=True, profile_slot=ProfileSlot.MONTHLY_BILL,
    )
    budgeted = Memory(
        id=uuid4(), entity_id="entity", memory_type=MemoryType.PREFERENCE,
        observation="Prefers a quiet battery", base_confidence=0.95,
        profile_slot=ProfileSlot.NONE,
    )
    monkeypatch.setattr(session, "list_memories", lambda *_args, **_kwargs: [superseded, budgeted])

    trace = {entry["memory_id"]: entry["reason"] for entry in session._build_excluded_memory_trace("entity", set())}

    assert trace[str(superseded.id)] == "Superseded by a newer confirmed memory; retained for audit."
    assert trace[str(budgeted.id)] == "Not selected within the configured memory budget for this answer."


def test_explain_trace_contract_preserves_auditable_exclusion_details():
    from app.api.contracts import ExcludedMemoryDTO, ExplainTraceDTO, MemoryDTO, ProvenanceDTO

    memory = MemoryDTO(
        id="prior", observation="Monthly bill was R3,200", memory_type="fact",
        profile_slot="monthly_bill", confidence=0.95, status="retained",
        provenance=ProvenanceDTO(source_verified=False),
    )
    trace = ExplainTraceDTO(
        available_memory_ids=["current"],
        excluded_memories=[ExcludedMemoryDTO(
            memory_id="prior",
            reason="Superseded by a newer confirmed memory; retained for audit.",
            memory=memory,
        )],
    ).model_dump(by_alias=True)

    assert trace["availableMemoryIds"] == ["current"]
    assert trace["excludedMemories"][0]["memoryId"] == "prior"
    assert trace["excludedMemories"][0]["memory"]["observation"] == "Monthly bill was R3,200"


def test_processing_lease_only_recovers_expired_or_legacy_stale_rows():
    from app.chat.session import _processing_lease_is_stale

    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    assert _processing_lease_is_stale(
        {"lease_expires_at": now + timedelta(seconds=1), "updated_at": now}, now, 70
    ) is False
    assert _processing_lease_is_stale(
        {"lease_expires_at": now - timedelta(seconds=1), "updated_at": now}, now, 70
    ) is True
    assert _processing_lease_is_stale(
        {"lease_expires_at": None, "updated_at": now - timedelta(seconds=71)}, now, 70
    ) is True


def test_qwen_retry_refuses_to_start_after_the_invocation_budget_expires():
    from app.chat import qwen_client
    import time

    settings = SimpleNamespace(
        qwen_max_retries=3,
        qwen_timeout_seconds=30,
        qwen_attempt_timeout_seconds=12,
        qwen_retry_initial_delay_seconds=0.5,
        qwen_invocation_budget_seconds=42,
    )

    class NeverCalledClient:
        def post(self, *_args, **_kwargs):
            raise AssertionError("A request must not start once the budget is exhausted")

    with pytest.raises(qwen_client.QwenInvocationDeadlineExceeded):
        qwen_client._post_with_retry(
            NeverCalledClient(), "https://example.invalid", settings=settings,
            deadline=time.monotonic() - 0.01,
        )


def test_chat_time_tool_surface_never_exposes_direct_memory_writes(monkeypatch):
    from app.chat import qwen_client

    settings = SimpleNamespace(
        qwen_api_key="test-key",
        qwen_model_chat="qwen-test",
        qwen_api_base_url="https://example.invalid/api/v1",
        qwen_timeout_seconds=30,
        qwen_attempt_timeout_seconds=12,
        qwen_invocation_budget_seconds=42,
        qwen_max_retries=1,
        qwen_retry_initial_delay_seconds=0.5,
    )
    calls: list[dict] = []
    responses = [
        {
            "output": {
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call-1",
                            "function": {
                                "name": "write_memory",
                                "arguments": '{"observation":"unverified"}',
                            },
                        }],
                    }
                }]
            },
            "usage": {},
        },
        {"output": {"choices": [{"message": {"content": "Safe reply"}}]}, "usage": {}},
    ]

    class FakeResponse:
        headers = {}

        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, **kwargs):
            calls.append(kwargs["json"])
            return FakeResponse(responses.pop(0))

    monkeypatch.setattr(qwen_client.httpx, "Client", FakeClient)
    client = qwen_client.QwenClient()
    client.settings = settings

    assert client.complete_with_tools("system", [{"role": "user", "content": "hello"}], "entity") == "Safe reply"
    assert all(
        tool["function"]["name"] != "write_memory"
        for tool in calls[0]["tools"]
    )
    tool_messages = [
        message
        for message in calls[1]["input"]["messages"]
        if message.get("role") == "tool"
    ]
    assert "Memory changes are saved only" in tool_messages[0]["content"]


def test_population_prior_hook_is_non_durable_compatibility_noop():
    from app.memory import priors

    assert not hasattr(priors, "write_from_draft")
    assert priors.seed_population_priors("entity", "Need backup", uuid4()) is None
