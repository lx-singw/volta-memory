# Volta Memory — Redesigned Benchmark Results

**Date:** 2026-07-19 13:10:00 UTC  
**Model ID:** `qwen-max`  
**Git Commit:** `ee81fd71`  

## Comparative Systems Summary

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|---|---|
| A_no_memory | 0.1212 (8/66) | 0.0000 (0/6) | 0.8750 (21/24) | 0.3704 (30/81) | 4779 | $0.001529 | 0 | $0.000000 | 33 |
| B_full_context | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8519 (69/81) | 4839 | $0.001855 | 0 | $0.000000 | 33 |
| C_naive_rag | 0.9091 (60/66) | 0.0000 (0/6) | 0.2083 (5/24) | 0.7531 (61/81) | 10903 | $0.001638 | 0 | $0.000000 | 33 |
| D_volta_memory | 0.8333 (55/66) | 0.5000 (3/6) | 0.4583 (11/24) | 0.8272 (67/81) | 8856 | $0.002118 | 21906 | $0.006768 | 33 |

## Database Lifecycle Verification

| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |
|---|---|---|---|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 0.8947 (51/57) | 1.0000 (6/6) | 0.0000 (0/3) |
