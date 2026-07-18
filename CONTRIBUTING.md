# Volta Memory — Contributing & Governance
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**

---

## Table of Contents
- [1. Code of Conduct Summary](#1-code-of-conduct-summary)
- [2. The Three Scoped Contribution Shapes](#2-the-three-scoped-contribution-shapes)
- [3. Contribution Process](#3-contribution-process)
- [4. Maintainer Responsibilities](#4-maintainer-responsibilities)
- [5. Decision-Making for Contested Changes](#5-decision-making-for-contested-changes)
- [6. Licensing of Contributions](#6-licensing-of-contributions)

---

## 1. Code of Conduct Summary

Contributors are expected to engage respectfully, assume good faith, and focus disagreement on technical merit rather than personal characterization. A full Contributor Covenant–style code of conduct file is available at `CODE_OF_CONDUCT.md` at the repository root.

---

## 2. The Three Scoped Contribution Shapes

### 2.1 New LLM Backend

Implement the `LLMBackend` protocol:
```python
class LLMBackend(Protocol):
    def complete(self, prompt: str, max_tokens: int) -> str: ...
    def complete_stream(self, prompt: str, max_tokens: int) -> Iterator[str]: ...
    def embed(self, text: str) -> list[float]: ...
```
A conformance test suite (ships with the package) any new backend must pass before a PR is accepted. The `OpenAIBackend` is the model to follow for a new implementation's shape and file structure.

### 2.2 New Domain Example

A new directory under `examples/`, following the pattern of `qwen_energy_advisor/` and `qwen_study_coach/`: a domain-specific system prompt, a short README explaining the domain and why memory matters for it, and a short write-up of whether any decay/importance tuning was needed for that domain.

### 2.3 Decay/Stability Function Alternatives

The `stability.py` module's `growth_factor` and lambda constants are configurable via the documented interface for stability functions. A contributor proposing an alternative forgetting curve can benchmark their proposal against the default using the existing eval harness.

---

## 3. Contribution Process

1. Open an issue first for anything beyond a trivial fix — describe the proposed change and which of the three shapes it falls under.
2. A maintainer responds within 5 business days acknowledging the issue and indicating whether it fits the roadmap.
3. PRs reference the originating issue, include tests appropriate to the contribution shape (conformance tests for a new backend, the domain write-up for a new example, eval harness results for a stability function alternative).
4. CI must pass — existing test suite, coverage threshold, and mypy strict-mode check all green before review begins.
5. At least one maintainer approval required before merge.

---

## 4. Maintainer Responsibilities

The first several external contributions receive fast, personal responses specifically because early contributor experience disproportionately determines whether a project earns a second contribution at all.

---

## 5. Decision-Making for Contested Changes

For anything outside the three scoped shapes — a proposed architectural change, a new memory type in the taxonomy, a change to the MCP tool schema — the maintainers make the final call, but are expected to state their reasoning publicly on the issue, consistent with the explainability principle built into the product itself.

---

## 6. Licensing of Contributions

All contributions are made under the same license as the repository (MIT). Contributors retain copyright to their contribution but license it under the project's terms by submitting a PR.
