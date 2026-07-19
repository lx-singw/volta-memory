# Volta Memory — Redesigned Benchmark Results

**Date:** 2026-07-19 18:24:58 UTC  
**Model ID:** `qwen-max`  
**Evaluator Code Commit:** `cf845c7e`  
**Report Reference Commit:** `4f6ee78a`  

## Comparative Systems Summary

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|---|---|
| A_no_memory | 0.1515 (10/66) | 0.0000 (0/6) | 0.8333 (20/24) | 0.3704 (30/81) | 6289 | $0.001564 | 0 | $0.000000 | 33 |
| B_full_context | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8642 (70/81) | 5885 | $0.001911 | 0 | $0.000000 | 33 |
| C_naive_rag | 0.9091 (60/66) | 0.0000 (0/6) | 0.1667 (4/24) | 0.7654 (62/81) | 13042 | $0.001722 | 0 | $0.000000 | 33 |
| D_volta_memory | 0.8485 (56/66) | 0.5000 (3/6) | 0.7500 (18/24) | 0.8395 (68/81) | 10329 | $0.002037 | 25752 | $0.006808 | 33 |

## Database Lifecycle Verification

| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |
|---|---|---|---|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 0.8596 (49/57) | 1.0000 (6/6) | 0.3333 (1/3) |
