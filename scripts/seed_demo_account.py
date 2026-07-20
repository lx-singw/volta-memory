import os
import sys
import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import dotenv_values
import psycopg

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    env_path = repo_root / ".env"
    if not env_path.exists():
        print(f"Error: .env not found at {env_path}")
        return 1

    env = dotenv_values(env_path)
    db_url = env.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set in .env")
        return 1

    entity_id = "demo-consumer-1"
    now = datetime.now(timezone.utc)
    time_s1 = now - timedelta(days=21)
    time_s2 = now - timedelta(days=3)

    print(f"Connecting to database to seed entity '{entity_id}'...")
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO entities (id, entity_type, is_read_only)
                    VALUES (%s, 'showcase', true)
                    ON CONFLICT (id) DO UPDATE SET entity_type = 'showcase', is_read_only = true, updated_at = now()
                    """,
                    (entity_id,),
                )
                # 1. Clean up existing demo data
                print("Cleaning up old demo data...")
                cur.execute("DELETE FROM memory_lifecycle_events WHERE entity_id = %s", (entity_id,))
                cur.execute("DELETE FROM explain_traces WHERE message_id IN (SELECT id FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE entity_id = %s))", (entity_id,))
                cur.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE entity_id = %s)", (entity_id,))
                cur.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
                cur.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))
                cur.execute("DELETE FROM transcript_chunks WHERE entity_id = %s", (entity_id,))

                # 2. Seed Session 1 (21 days ago)
                print("Seeding Session 1 (21 days ago)...")
                s1_id = uuid4()
                cur.execute(
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
                    cur.execute(
                        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
                        (msg_id, conv_id, role, content, t)
                    )

                # Memories created in Session 1
                mem1_bill_id = uuid4()
                mem1_pref_id = uuid4()
                mem1_pet_id = uuid4()

                cur.execute(
                    """
                    INSERT INTO memories (
                        id, entity_id, memory_type, observation, evidence,
                        base_confidence, reinforcement_count, cross_session_reinforcement_count,
                        first_observed_at, last_reinforced_at,
                        source_session_id, importance_score, importance_reasoning,
                        plausibility_flag, source, profile_slot, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s, %s, 0.85, 'Direct financial context for sizing', 'plausible', 'individual', 'monthly_bill', %s)
                    """,
                    (mem1_bill_id, entity_id, "fact", "User has a monthly bill of R3,200",
                     json.dumps({"source_quote": "My bill is R3,200", "source_turn_index": 3}),
                     0.90, time_s1, time_s1, s1_id, time_s1)
                )

                cur.execute(
                    """
                    INSERT INTO memories (
                        id, entity_id, memory_type, observation, evidence,
                        base_confidence, reinforcement_count, cross_session_reinforcement_count,
                        first_observed_at, last_reinforced_at,
                        source_session_id, importance_score, importance_reasoning,
                        plausibility_flag, source, profile_slot, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s, %s, 0.95, 'Primary driver of energy system choice', 'plausible', 'individual', 'backup_priority', %s)
                    """,
                    (mem1_pref_id, entity_id, "preference", "Backup power is user's primary motivation",
                     json.dumps({"source_quote": "backup power is my absolute priority", "source_turn_index": 3}),
                     0.95, time_s1, time_s1, s1_id, time_s1)
                )

                cur.execute(
                    """
                    INSERT INTO memories (
                        id, entity_id, memory_type, observation, evidence,
                        base_confidence, reinforcement_count, cross_session_reinforcement_count,
                        first_observed_at, last_reinforced_at,
                        source_session_id, importance_score, importance_reasoning,
                        plausibility_flag, source, profile_slot, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s, %s, 0.10, 'Irrelevant personal detail', 'plausible', 'individual', 'none', %s)
                    """,
                    (mem1_pet_id, entity_id, "fact", "User has a pet parrot named Charlie who likes to sing",
                     json.dumps({"source_quote": "I also have a pet parrot named Charlie who loves to sing", "source_turn_index": 3}),
                     0.80, time_s1, time_s1, s1_id, time_s1)
                )

                # 3. Seed Session 2 (3 days ago)
                print("Seeding Session 2 (3 days ago)...")
                s2_id = uuid4()
                cur.execute(
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
                    cur.execute(
                        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
                        (msg_id, conv_id, role, content, t)
                    )

                # Write correction memory first (so the ID exists for referencing)
                mem2_bill_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO memories (
                        id, entity_id, memory_type, observation, evidence,
                        base_confidence, reinforcement_count, cross_session_reinforcement_count,
                        first_observed_at, last_reinforced_at,
                        source_session_id, importance_score, importance_reasoning,
                        plausibility_flag, source, profile_slot, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s, %s, %s, 0.90, 'Updated monthly bill context', 'plausible', 'individual', 'monthly_bill', %s)
                    """,
                    (mem2_bill_id, entity_id, "correction", "User has a monthly bill of R3,800",
                     json.dumps({
                         "source_quote": "Actually, my bill is more like R3,800 on average now.",
                         "source_turn_index": 3,
                         "supersedes": {
                             "memory_id": str(mem1_bill_id),
                             "observation": "User has a monthly bill of R3,200",
                             "source_quote": "My bill is R3,200"
                         }
                     }),
                     0.95, time_s2, time_s2, s2_id, time_s2)
                )

                # Now update/supersede the R3,200 memory
                cur.execute(
                    "UPDATE memories SET is_superseded = true, superseded_by_id = %s WHERE id = %s",
                    (mem2_bill_id, mem1_bill_id)
                )

                # Reinforce preference memory (backup)
                cur.execute(
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

                provenance_rows = [
                    (mem1_bill_id, s1_id, "My bill is R3,200", 3, False),
                    (mem1_pref_id, s1_id, "backup power is my absolute priority", 3, False),
                    (mem1_pet_id, s1_id, "I also have a pet parrot named Charlie who loves to sing", 3, False),
                    (mem2_bill_id, s2_id, "Actually, my bill is more like R3,800 on average now.", 3, False),
                ]
                for memory_id, source_session_id, quote, turn_index, is_constraint in provenance_rows:
                    cur.execute(
                        """
                        SELECT id FROM messages
                        WHERE conversation_id = %s AND role = 'user' AND position(%s IN content) > 0
                        ORDER BY created_at ASC LIMIT 1
                        """,
                        (source_session_id, quote),
                    )
                    source_message = cur.fetchone()
                    cur.execute(
                        """
                        INSERT INTO memory_provenance (
                            id, memory_id, original_user_message_id, source_session_id,
                            source_turn_index, source_quote, source_verified, is_constraint
                        ) VALUES (%s, %s, %s, %s, %s, %s, true, %s)
                        ON CONFLICT (memory_id) DO UPDATE SET
                            original_user_message_id = EXCLUDED.original_user_message_id,
                            source_session_id = EXCLUDED.source_session_id,
                            source_turn_index = EXCLUDED.source_turn_index,
                            source_quote = EXCLUDED.source_quote,
                            source_verified = true,
                            is_constraint = EXCLUDED.is_constraint
                        """,
                        (uuid4(), memory_id, source_message[0], source_session_id, turn_index, quote, is_constraint),
                    )
                cur.execute(
                    """
                    INSERT INTO memory_relations (id, source_memory_id, target_memory_id, relation_type, source_session_id)
                    VALUES (%s, %s, %s, 'supersedes', %s)
                    ON CONFLICT (source_memory_id, target_memory_id, relation_type) DO NOTHING
                    """,
                    (uuid4(), mem1_bill_id, mem2_bill_id, s2_id),
                )
                cur.execute(
                    """
                    INSERT INTO memory_lifecycle_events (
                        id, entity_id, session_id, action, before_memory_id, after_memory_id, display_payload
                    ) VALUES (%s, %s, %s, 'corrected', %s, %s, %s)
                    """,
                    (
                        uuid4(), entity_id, s2_id, mem1_bill_id, mem2_bill_id,
                        json.dumps({"operation": "corrected", "before": {"id": str(mem1_bill_id), "observation": "User has a monthly bill of R3,200"}, "after": {"id": str(mem2_bill_id), "observation": "User has a monthly bill of R3,800"}}),
                    ),
                )

                print("[SUCCESS] Seeding complete! Demo account is ready for testing.")
    except Exception as e:
        print(f"[ERROR] Seeding failed: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
