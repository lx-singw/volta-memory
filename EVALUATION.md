# Evaluation Method and Evidence

## Source of truth

`backend/eval/artifacts/evaluation-summary.json` is the machine-readable source for the benchmark report, deck, and submission claims. `BENCHMARKS.md` is generated from it; do not hand-edit metric values.

The checked-in artifact documents one completed run:

- run ID `6a51d3eb-a02c-4511-9ace-f8586a431164`;
- 11 personas, 4 systems, and 3 replicates (132 cases);
- 132/132 successful cases;
- Qwen chat model `qwen-max`;
- evaluator commit `cf845c7e` as reported by the completed run.

The artifact is evidence for that exact evaluator commit, not a substitute for a
release-candidate rerun. Any code change that affects extraction, lifecycle
writes, retrieval, or evaluation policy must be committed and followed by a
new full sweep before its metrics are used in submission copy or a release deck.

`evaluation-cases.jsonl` is a sanitised, checksum-covered case artifact. It retains metrics, call telemetry, and status while excluding transcript content, provider payloads, and detailed errors.

## Systems

- **A - no memory:** answers without historical memory.
- **B - full context:** supplies history without lifecycle governance.
- **C - naive RAG:** retrieves independent semantic chunks.
- **D - Volta:** persists typed memory, resolves corrections, applies retrieval policy, and writes lifecycle state.

## Measures

- Recall accuracy: expected current facts appear in active context or answer.
- Correction accuracy: the new fact is present and an old value is not used as current advice.
- Forgetting accuracy: irrelevant or decayed facts are absent from active context and answer.
- Downstream quality: answer-level expected and prohibited references.
- Database lifecycle: stored, superseded, and excluded states for System D.
- Telemetry: per-call token counts, latency, and estimated cost from actual Qwen calls; online response metrics and offline end-session writes are reported separately.

## How to reproduce

```bash
cd backend
EVAL_MODE=true python3 -m eval.run_eval
cd ..
python3 scripts/generate_evaluation_artifacts.py --write-benchmarks
python3 scripts/generate_slide_deck.py
```

The full sweep calls Qwen and incurs real cost. Use the smoke flag only for implementation validation; never present a smoke result as the comparative evaluation.

## Interpretation and limitations

For evaluator commit `cf845c7e`, the artifact supports a clear lifecycle claim: Volta persisted all six tested supersession chains and achieved 75.0% forgetting accuracy, versus 25.0% for full history and 16.7% for naive RAG in this run. It also shows real trade-offs: downstream correction is 50.0%, recall is below full context, and offline extraction adds cost and latency. The deck and submission must preserve those qualifiers and must be regenerated after a post-run code change.
