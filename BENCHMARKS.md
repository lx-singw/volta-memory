# Volta Memory — Redesigned Benchmark Results

**Date:** 2026-07-19 13:29:48 UTC  
**Model ID:** `qwen-max`  
**Git Commit:** `7ff5dbf9`  

## Comparative Systems Summary

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|---|---|
| A_no_memory | 0.0000 (0/1) | N/A | 1.0000 (2/2) | 0.6667 (2/3) | 5352 | $0.001446 | 0 | $0.000000 | 1 |
| B_full_context | 1.0000 (1/1) | N/A | 0.0000 (0/2) | 1.0000 (3/3) | 4660 | $0.001500 | 0 | $0.000000 | 1 |
| C_naive_rag | 1.0000 (1/1) | N/A | 0.0000 (0/2) | 0.6667 (2/3) | 7546 | $0.001428 | 0 | $0.000000 | 1 |
| D_volta_memory | 1.0000 (1/1) | N/A | 1.0000 (2/2) | 1.0000 (3/3) | 8572 | $0.002338 | 17927 | $0.004286 | 1 |

## Database Lifecycle Verification

| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |
|---|---|---|---|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 1.0000 (2/2) | N/A | 1.0000 (1/1) |
