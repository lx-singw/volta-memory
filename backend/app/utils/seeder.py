import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.db import get_connection

def seed_entity(entity_id: str):
    now = datetime.now(timezone.utc)
    time_s1 = now - timedelta(days=21)
    time_s2 = now - timedelta(days=3)

    with get_connection() as conn:
        # 1. Clean up existing demo data
        conn.execute(
            """
            DELETE FROM explain_traces 
            WHERE message_id IN (
                SELECT id FROM messages 
                WHERE conversation_id IN (
                    SELECT id FROM conversations WHERE entity_id = %s
                )
            )
            """, 
            (entity_id,)
        )
        conn.execute(
            """
            DELETE FROM messages 
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE entity_id = %s
            )
            """, 
            (entity_id,)
        )
        conn.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
        conn.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))
        conn.execute("DELETE FROM transcript_chunks WHERE entity_id = %s", (entity_id,))

        # 2. Seed Session 1 (21 days ago)
        s1_id = uuid4()
        conn.execute(
            "INSERT INTO conversations (id, entity_id, started_at, ended_at, extraction_completed) VALUES (%s, %s, %s, %s, true)",
            (s1_id, entity_id, time_s1, time_s1 + timedelta(minutes=15))
        )

        # Messages in Session 1
        messages_s1 = [
            (uuid4(), s1_id, "user", "Hi, I'm looking into getting solar. Load-shedding is really bad in my area and I need backup power.", time_s1 + timedelta(minutes=1)),
            (uuid4(), s1_id, "assistant", "Hi there. Sizing a system depends on your bill. What is your monthly bill, and is backup or savings more important?", time_s1 + timedelta(minutes=2)),
            (uuid4(), s1_id, "user", "My bill is R3,200. Sashing the bill is good, but backup power is my absolute priority. I also have a pet parrot named Charlie who loves to sing.", time_s1 + timedelta(minutes=3)),
            (uuid4(), s1_id, "assistant", "Got it. I have noted backup power as priority, monthly bill R3,200, and your parrot Charlie.", time_s1 + timedelta(minutes=4)),
        ]
        for msg_id, conv_id, role, content, t in messages_s1:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
                (msg_id, conv_id, role, content, t)
            )

        # Memories created in Session 1
        mem1_bill_id = uuid4()
        mem1_pref_id = uuid4()
        mem1_pet_id = uuid4()

        conn.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source, created_at
            ) VALUES (%s, %s, 'fact', 'User has a monthly bill of R3,200', %s, 0.90, 1, 1, %s, %s, %s, 0.85, 'Direct financial context for sizing', 'plausible', 'individual', %s)
            """,
            (
                mem1_bill_id, entity_id,
                json.dumps({"source_quote": "My bill is R3,200", "source_turn_index": 3}),
                time_s1, time_s1, s1_id, time_s1
            )
        )

        conn.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source, created_at
            ) VALUES (%s, %s, 'preference', 'Backup power is user''s primary motivation', %s, 0.95, 1, 1, %s, %s, %s, 0.95, 'Primary driver of energy system choice', 'plausible', 'individual', %s)
            """,
            (
                mem1_pref_id, entity_id,
                json.dumps({"source_quote": "backup power is my absolute priority", "source_turn_index": 3}),
                time_s1, time_s1, s1_id, time_s1
            )
        )

        conn.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source, created_at
            ) VALUES (%s, %s, 'fact', 'User has a pet parrot named Charlie who likes to sing', %s, 0.80, 1, 1, %s, %s, %s, 0.10, 'Irrelevant personal detail', 'plausible', 'individual', %s)
            """,
            (
                mem1_pet_id, entity_id,
                json.dumps({"source_quote": "I also have a pet parrot named Charlie who loves to sing", "source_turn_index": 3}),
                time_s1, time_s1, s1_id, time_s1
            )
        )

        # 3. Seed Session 2 (3 days ago)
        s2_id = uuid4()
        conn.execute(
            "INSERT INTO conversations (id, entity_id, started_at, ended_at, extraction_completed) VALUES (%s, %s, %s, %s, true)",
            (s2_id, entity_id, time_s2, time_s2 + timedelta(minutes=10))
        )

        # Messages in Session 2
        messages_s2 = [
            (uuid4(), s2_id, "user", "Hey, standard follow up. I've had to review my monthly expenses.", time_s2 + timedelta(minutes=1)),
            (uuid4(), s2_id, "assistant", "Welcome back! Since backup power is your main focus and your bill was R3,200, how can I help?", time_s2 + timedelta(minutes=2)),
            (uuid4(), s2_id, "user", "Actually, my bill is more like R3,800 on average now.", time_s2 + timedelta(minutes=3)),
            (uuid4(), s2_id, "assistant", "Understood, I will update your bill amount to R3,800.", time_s2 + timedelta(minutes=4)),
        ]
        for msg_id, conv_id, role, content, t in messages_s2:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
                (msg_id, conv_id, role, content, t)
            )

        # Write correction memory first (so the ID exists for referencing)
        mem2_bill_id = uuid4()
        conn.execute(
            """
            INSERT INTO memories (
                id, entity_id, memory_type, observation, evidence,
                base_confidence, reinforcement_count, cross_session_reinforcement_count,
                first_observed_at, last_reinforced_at,
                source_session_id, importance_score, importance_reasoning,
                plausibility_flag, source, created_at
            ) VALUES (%s, %s, 'correction', 'User has a monthly bill of R3,800', %s, 0.95, 1, 1, %s, %s, %s, 0.90, 'Updated monthly bill context', 'plausible', 'individual', %s)
            """,
            (
                mem2_bill_id, entity_id,
                json.dumps({
                    "source_quote": "Actually, my bill is more like R3,800 on average now.",
                    "source_turn_index": 3,
                    "supersedes": {
                        "memory_id": str(mem1_bill_id),
                        "observation": "User has a monthly bill of R3,200",
                        "source_quote": "My bill is R3,200"
                    }
                }),
                time_s2, time_s2, s2_id, time_s2
            )
        )

        # Now update/supersede the R3,200 memory
        conn.execute(
            "UPDATE memories SET is_superseded = true, superseded_by_id = %s WHERE id = %s",
            (mem2_bill_id, mem1_bill_id)
        )

        # Reinforce preference memory (backup)
        conn.execute(
            """
            UPDATE memories
            SET reinforcement_count = 2,
                cross_session_reinforcement_count = 2,
                base_confidence = 0.98,
                last_reinforced_at = %s
            WHERE id = %s
            """,
            (time_s2, mem1_pref_id)
        )
