# Volta Memory — Redesigned Benchmark Results

**Date:** 2026-07-19 18:15:10 UTC  
**Model ID:** `qwen-max`  
**Evaluator Code Commit:** `cf845c7e`  
**Report Reference Commit:** `1e44d24d`  

## Comparative Systems Summary

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|---|---|
| A_no_memory | 0.1364 (9/66) | 0.0000 (0/6) | 0.7917 (19/24) | 0.3457 (28/81) | 5500 | $0.001542 | 0 | $0.000000 | 33 |
| B_full_context | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8519 (69/81) | 6856 | $0.001813 | 0 | $0.000000 | 33 |
| C_naive_rag | 0.9091 (60/66) | 0.0000 (0/6) | 0.1667 (4/24) | 0.7901 (64/81) | 10573 | $0.001639 | 0 | $0.000000 | 33 |
| D_volta_memory | 0.8333 (55/66) | 0.5000 (3/6) | 0.6667 (16/24) | 0.8148 (66/81) | 9338 | $0.002010 | 22694 | $0.007148 | 33 |

## Database Lifecycle Verification

| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |
|---|---|---|---|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 0.8947 (51/57) | 1.0000 (6/6) | 1.0000 (3/3) |
