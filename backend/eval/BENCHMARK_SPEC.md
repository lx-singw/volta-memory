# Volta Memory Agent — Public Evaluation Benchmark Spec
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

This directory contains the public benchmark dataset specification for evaluating multi-turn, cross-session memory agent retrieval systems.

---

## 1. Dataset Overview

The benchmark consists of **20 detailed test personas** (found in [personas/](file:///wsl.localhost/Ubuntu/home/lx_singw/projects/volta-memory/backend/eval/personas/)) designed to challenge memory engines on:
1.  **Temporal Recall**: Remembering facts across session boundaries.
2.  **Superseding/Correction**: Safely ignoring out-of-date or explicitly corrected preferences.
3.  **Noiseless Filtering**: Not retrieving irrelevant or decayed details in new contexts.
4.  **Adversarial Resilience**: Defending against malicious inputs (jailbreaks or prompt injection) inside historical memory records.

---

## 2. File Format Specification

Each persona is defined in a structured YAML file with the following schema:
```yaml
id: <string_unique_id>
entity_id: <string_uuid_or_id>
theme: <string_brief_description>
sessions:
  - session_number: <int>
    messages:
      - role: "user" | "assistant"
        content: <string_text>
ground_truth:
  should_recall_in_session_2:
    - <list_of_phrases_or_keywords>
  should_supersede: <boolean>
  adversarial: <boolean>
```

---

## 3. Persona Taxonomy

The benchmark is categorized into the following challenge groups:

| File Name | Challenge Category | Focus Area |
| :--- | :--- | :--- |
| `persona_01_backup_priority.yaml` | Recall Prioritization | Prefers backup over cost |
| `persona_02_cost_priority.yaml` | Recall Prioritization | Prefers cost savings over backup |
| `persona_03_hybrid_motivation.yaml` | Complex Recall | Multiple energy sources/tariffs |
| `persona_04_large_home.yaml` | Sizing Requirements | Large scale consumption profile |
| `persona_05_small_apartment.yaml` | Sizing Requirements | Limited roof space constraint |
| `persona_06_financing_interest.yaml` | Financing Options | Loan vs interest rate query |
| `persona_07_tariff_complexity.yaml` | Tariff Rates | Time-of-use (TOU) tariff mapping |
| `persona_08_battery_sizing.yaml` | Capacity Sizing | Off-grid battery capacity requirements |
| `persona_09_installer_skeptic.yaml` | General Trust | Fact-checking warranty details |
| `persona_10_solar_newbie.yaml` | Education | Explaining basic net metering concepts |
| `persona_11_technical_user.yaml` | Exact Specifications | Specific inverter model efficiency (98.5%) |
| `persona_12_elderly_homeowner.yaml` | Simplicity | Avoids jargon, focus on automated comfort |
| `persona_13_landlord_rental.yaml` | ROI Constraints | Split incentive between tenant/landlord |
| `persona_14_future_expansion.yaml` | Planning | Future expansion sizing requirements |
| `persona_15_correction_bill.yaml` | Memory Superseding | Changes average monthly bill details |
| `persona_16_correction_priority.yaml` | Memory Superseding | Changes priority from green to cost |
| `persona_17_decay_irrelevant.yaml` | Memory Decay | Mentions irrelevant pet detail (should decay) |
| `persona_18_reinforced_preference.yaml` | Reinforcement | Re-states preference (increases stability) |
| `persona_19_consolidation.yaml` | Consolidation | Standard candidate for semantic synthesis |
| `persona_20_adversarial.yaml` | Security Defense | Injects jailbreak attempts in session history |

---

## 4. Run Instructions

To run the benchmark evaluation harness locally against any target memory engine:
```bash
export PYTHONPATH=backend
python3 backend/eval/run_eval.py
```
This runs four system variants (**System A, B, C, D**) against all 20 personas, evaluating recall accuracy, cost usage, and security defense, producing a Markdown benchmark table output in `BENCHMARKS.md`.

---

## 5. Licensing

The benchmark personas and evaluation harness are licensed under the **Creative Commons Attribution 4.0 International License (CC-BY-4.0)**. The code wrappers are licensed under the **MIT License**.
