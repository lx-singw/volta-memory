# Volta Memory — Redesigned Benchmark Results

**Date:** 2026-07-19 14:56:34 UTC  
**Model ID:** `qwen-max`  
**Git Commit:** `cf845c7e`  

## Comparative Systems Summary

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Offline Latency P50 (ms) | Offline Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|---|---|
| A_no_memory | 0.1364 (9/66) | 0.0000 (0/6) | 0.8333 (20/24) | 0.3580 (29/81) | 4763 | $0.001603 | 0 | $0.000000 | 33 |
| B_full_context | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8272 (67/81) | 4933 | $0.001942 | 0 | $0.000000 | 33 |
| C_naive_rag | 0.9091 (60/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8148 (66/81) | 9782 | $0.001585 | 0 | $0.000000 | 33 |
| D_volta_memory | 0.8276 (48/58) | 0.7500 (3/4) | 0.6667 (12/18) | 0.7761 (52/67) | 11137 | $0.002019 | 32205 | $0.007248 | 28 |

## Database Lifecycle Verification

| System | DB Stored Accuracy | DB Superseded Accuracy | DB Excluded Accuracy |
|---|---|---|---|
| A_no_memory | N/A | N/A | N/A |
| B_full_context | N/A | N/A | N/A |
| C_naive_rag | N/A | N/A | N/A |
| D_volta_memory | 0.8571 (42/49) | 1.0000 (4/4) | 0.6667 (2/3) |
