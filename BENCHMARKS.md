# Volta Memory Benchmark Results

> This report is generated from [`evaluation-summary.json`](backend/eval/artifacts/evaluation-summary.json). Do not hand-edit metric values.

## Run provenance

- Run ID: `6a51d3eb-a02c-4511-9ace-f8586a431164`
- Completed: `2026-07-19T20:24:58+00:00`
- Evaluator code commit: `cf845c7e`
- Qwen chat model: `qwen-max`
- Cases: `132/132` successful; `0` failed
- Sanitised case artifact SHA-256: `908a7b2bc6d25abbcb717d62aa2b1896ac3b1b49059b1883cb28f5c224bab4d5`

## Comparative systems

| System | Recall accuracy | Correction accuracy | Forgetting accuracy | Downstream quality | Online latency P50 (ms) | Online cost avg (USD) | Offline latency P50 (ms) | Offline cost avg (USD) | Runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_no_memory | 0.1515 (10/66) | 0.0000 (0/6) | 0.8333 (20/24) | 0.3704 (30/81) | 6289 | $0.001564 | 0 | $0.000000 | 33 |
| B_full_context | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8642 (70/81) | 5885 | $0.001911 | 0 | $0.000000 | 33 |
| C_naive_rag | 0.9091 (60/66) | 0.0000 (0/6) | 0.1667 (4/24) | 0.7654 (62/81) | 13042 | $0.001722 | 0 | $0.000000 | 33 |
| D_volta_memory | 0.8485 (56/66) | 0.5000 (3/6) | 0.7500 (18/24) | 0.8395 (68/81) | 10329 | $0.002037 | 25752 | $0.006808 | 33 |

## Database lifecycle verification

| System | DB stored accuracy | DB superseded accuracy | DB excluded accuracy |
|---|---:|---:|---:|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 0.8596 (49/57) | 1.0000 (6/6) | 0.3333 (1/3) |

## Interpretation

The report is comparative evidence, not a blanket quality claim. Volta's correction, selective-forgetting, recall, latency, and cost results should be read together with the per-case artifact and the documented baseline definitions in [EVALUATION.md](EVALUATION.md).
