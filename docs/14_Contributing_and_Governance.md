# Volta Memory — Contributing & Governance
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**The actual content of the repository's CONTRIBUTING.md, written in full here for review before publishing**

---

## Table of Contents
- [1. Why This Document Exists Separately](#1-why-this-document-exists-separately)
- [2. Code of Conduct Summary](#2-code-of-conduct-summary)
- [3. The Three Scoped Contribution Shapes](#3-the-three-scoped-contribution-shapes)
- [4. Contribution Process](#4-contribution-process)
- [5. Maintainer Responsibilities](#5-maintainer-responsibilities)
- [6. Decision-Making for Contested Changes](#6-decision-making-for-contested-changes)
- [7. Licensing of Contributions](#7-licensing-of-contributions)

---

## 1. Why This Document Exists Separately

Document 08 §7 already specifies the three scoped contribution shapes conceptually. This document is the actual, ready-to-publish `CONTRIBUTING.md` content — written so a first-time external contributor reading the repository needs no other context to understand how to propose a change, what will be reviewed, and how decisions get made. Governance clarity is itself part of what makes a project genuinely adoptable, per the Problem Value & Impact case built in Document 08.

---

## 2. Code of Conduct Summary

Standard, unremarkable, and stated briefly rather than reproduced in full: contributors are expected to engage respectfully, assume good faith, and focus disagreement on technical merit rather than personal characterization. A full Contributor Covenant–style code of conduct file should be added at `CODE_OF_CONDUCT.md` at repo root, referenced but not reproduced here.

---

## 3. The Three Scoped Contribution Shapes

Restated from Document 08 §7 with full operational detail for each:

### 3.1 New LLM Backend

Implement the `LLMBackend` protocol (Document 08 §2):
```python
class LLMBackend(Protocol):
    def complete(self, prompt: str, max_tokens: int) -> str: ...
    def complete_stream(self, prompt: str, max_tokens: int) -> Iterator[str]: ...
    def embed(self, text: str) -> list[float]: ...
```
A conformance test suite (ships with the package) any new backend must pass before a PR is accepted — this keeps the bar objective rather than subjective maintainer judgment. The `OpenAIBackend` (used in the third reference example, Document 08 §2 and §8) is the model to follow for a new implementation's shape and file structure.

### 3.2 New Domain Example

A new directory under `examples/`, following the pattern of `qwen_energy_advisor/` and `qwen_study_coach/`: a domain-specific system prompt, a short README explaining the domain and why memory matters for it (drawing on the applicability reasoning in Document 08 §3 as a template for the kind of justification expected), and — this is the part that makes the contribution genuinely useful rather than decorative — a short write-up of whether any decay/importance tuning was needed for that domain, since a domain requiring no tuning at all is itself useful signal that the defaults generalize, and a domain requiring tuning is useful signal for the core library's roadmap.

### 3.3 Decay/Stability Function Alternatives

The `stability.py` module's `growth_factor` and lambda constants (Design Doc §12) are configurable via the documented `LLMBackend`-adjacent interface for stability functions. A contributor proposing an alternative forgetting curve can benchmark their proposal against the default using the existing eval harness (Design Doc §14) — the harness is designed to be re-run against any parameter set, not just the ones shipped by default, meaning a contribution in this category comes with its own objective evidence rather than a subjective claim of improvement.

---

## 4. Contribution Process

1. Open an issue first for anything beyond a trivial fix — describes the proposed change and which of the three shapes (Section 3) it falls under, or states clearly if it's something else entirely
2. A maintainer responds within 5 business days acknowledging the issue and indicating whether it fits the current roadmap (Document 12) or is out of scope
3. PRs reference the originating issue, include tests appropriate to the contribution shape (conformance tests for a new backend, the domain write-up for a new example, eval harness results for a stability function alternative)
4. CI must pass — existing test suite, coverage threshold (Document 02's `coverage_report.py`), and mypy strict-mode check all green before review begins
5. At least one maintainer approval required before merge

---

## 5. Maintainer Responsibilities

Per the Phase 2 commitment in Document 12 (Roadmap): the first several external contributions should receive fast, personal responses specifically because early contributor experience disproportionately determines whether a project earns a second contribution at all. This is stated here as an explicit maintainer obligation, not left as an implicit hope.

---

## 6. Decision-Making for Contested Changes

For anything outside the three scoped shapes (Section 3) — a proposed architectural change, a new memory type in the taxonomy, a change to the MCP tool schema — the maintainer(s) make the final call, but are expected to state their reasoning publicly on the issue, consistent with the explainability principle already built into the product itself (Design Doc §16): a project whose own memory agent explains its reasoning should hold its governance to the same standard.

---

## 7. Licensing of Contributions

All contributions are made under the same license as the repository (MIT, per Document 01 §7 and Document 07's licensing gate). Contributors retain copyright to their contribution but license it under the project's terms by submitting a PR — standard open-source practice, stated explicitly here so it is never ambiguous.
