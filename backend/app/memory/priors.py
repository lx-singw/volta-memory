"""Legacy population-prior hook, intentionally non-durable."""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def seed_population_priors(entity_id: str, first_message: str, session_id: UUID) -> None:
    """Do nothing: inferred population priors must never become user memory.

    The old implementation wrote keyword-triggered assumptions directly into
    the durable store.  That bypassed source quote verification, the
    end-session idempotency receipt, and the lifecycle audit trail.  It remains
    as a no-op compatibility shim for offline callers until they can remove the
    import; product code must persist only source-linked session extraction.
    """
    del entity_id, first_message, session_id
    logger.info("Population-prior persistence is disabled; awaiting user-confirmed evidence.")
