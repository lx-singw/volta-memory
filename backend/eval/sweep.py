"""Grid search parameter sweep to find mathematically optimal decay constants."""

from __future__ import annotations

import logging
from app.config import get_settings
from eval.run_eval import _load_personas, _transcript_from_persona
from eval.baselines import system_d_volta_memory as system_d
from eval.ground_truth import load_persona_expectations
from eval.metrics import recall_accuracy, summarize_metrics

# Disable verbose logging during sweep
logging.getLogger().setLevel(logging.ERROR)


def sweep() -> None:
    settings = get_settings()
    from pathlib import Path
    personas = _load_personas(Path(settings.eval_persona_dir))
    
    # Grid search options
    lambda_pref_options = [0.005, 0.01, 0.02, 0.03]
    lambda_fact_options = [0.005, 0.01, 0.02, 0.03]
    
    best_accuracy = -1.0
    best_params = {}

    print("Starting parameter sweep grid search...")
    print(f"{'Preference Lambda':<20} | {'Fact Lambda':<20} | {'Recall Accuracy':<15}")
    print("-" * 62)

    for pref_l in lambda_pref_options:
        for fact_l in lambda_fact_options:
            # Inject parameters temporarily
            settings.decay_lambda_preference = pref_l
            settings.decay_lambda_fact = fact_l
            settings.decay_lambda_outcome = fact_l
            settings.decay_lambda_correction = pref_l
            
            rows = []
            for persona in personas:
                entity_id = f"sweep-{persona['id']}"
                transcript = _transcript_from_persona(persona)
                expectations = load_persona_expectations(persona)
                
                last_user = ""
                for session in persona.get("sessions", []):
                    for message in session.get("messages", []):
                        if message["role"] == "user":
                            last_user = message["content"]
                            
                result = system_d.respond(entity_id, transcript, last_user)
                observed = [item.get("observation", "") for item in result.get("memory_context_used", [])]
                
                rows.append({
                    "persona_id": persona["id"],
                    "recall_accuracy": recall_accuracy(expectations["recall"], observed + [result["reply"]]),
                    "forgetting_correctness": None,
                })
                
            summary = summarize_metrics(rows)
            acc = summary["recall_accuracy"]
            
            print(f"{pref_l:<20} | {fact_l:<20} | {acc:<15.4f}")
            
            if acc > best_accuracy:
                best_accuracy = acc
                best_params = {
                    "decay_lambda_preference": pref_l,
                    "decay_lambda_fact": fact_l
                }

    print("=" * 62)
    print(f"Sweep Optimal Parameters (Recall: {best_accuracy:.4f}):")
    print(f"  decay_lambda_preference: {best_params['decay_lambda_preference']}")
    print(f"  decay_lambda_fact: {best_params['decay_lambda_fact']}")


if __name__ == "__main__":
    sweep()
