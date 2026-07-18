# Volta Memory — Blog Post Draft
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**For the optional Blog Post Prize — a published post showing the build journey with Qwen Cloud**

---

## Table of Contents
- [1. Publishing Notes](#1-publishing-notes)
- [2. Draft Post](#2-draft-post)

---

## 1. Publishing Notes

Per Document 12's Phase 2 roadmap, this is distinct from the more technical Month-2 follow-up post — this draft is written specifically for the hackathon's Blog Post Prize submission, meaning it should read as a genuine build-journey narrative (what we tried, what didn't work, what we learned), not a polished marketing piece. Publish to a personal blog, Medium, dev.to, or Hashnode — any public platform satisfies the submission requirement, and dev.to specifically tends to have better organic reach within developer communities likely to include hackathon judges and Qwen Cloud's own team.

---

## 2. Draft Post

### Title: Why Your Memory Agent Needs to Forget on Purpose

Most "AI agent with memory" demos show the same thing: an agent that remembers everything you ever told it, forever. That's not memory — that's a database with extra steps. We wanted to build something that actually behaves like a good advisor remembers a client: durably retaining what matters, gracefully letting go of what doesn't, and getting more confident about the things you've told it more than once.

**The naive approaches we deliberately didn't build**

Before writing any decay logic, we looked at what most memory-agent projects do. Option one: stuff the whole conversation history into context every time. This doesn't scale, and worse, it never forgets — a throwaway comment from session one carries the same weight as a stated priority from session five, forever. Option two: embed everything into a vector store and retrieve by semantic similarity to the current question. This retrieves by *relevance to right now*, not by *importance* — a detail mentioned five times in idle chat can outrank a critical fact mentioned once with real weight behind it.

We built a third thing: a typed, confidence-scored memory store where every observation decays according to a real, cited mathematical model — not an arbitrary exponential, but the same functional shape behind Ebbinghaus's forgetting curve research and the spaced-repetition mathematics that power tools like Anki. Each time something is reinforced across a *separate* session (not just repeated within one rambling conversation), its stability window grows multiplicatively. Say something once, it fades in weeks. Say it three times across three separate conversations, and it's durable for months.

**The part that surprised us: letting the model score its own memory**

The obvious design assigns fixed decay rates by category — preferences decay slowly, one-off outcomes decay fast. We started there. But it's crude: not every preference is equally important, and not every outcome is equally disposable. So we let the model itself judge, at the moment of extraction, how consequential each observation is likely to be — and that self-scored importance directly modulates the decay rate for that specific memory, not just its category. A preference stated with real weight behind it decays half as fast as one mentioned in passing. We validated this wasn't just the model hallucinating confidence by benchmarking its self-assigned scores against a small human-labeled set — mean absolute error came in tight enough that we trust the mechanism, and we published the comparison rather than just asserting it works.

**Where Qwen Cloud's tool-calling changed our architecture mid-build**

Our first version pre-computed everything — rank the memories, pack them into a token budget, inject the result into the prompt, every single turn, whether or not that turn actually needed historical context. It worked, but it felt backwards: the model was a passive recipient of whatever we decided to hand it.

We rebuilt the memory engine as an MCP server, exposing `get_memory_context`, `check_memory_confidence`, and `write_memory` as tools Qwen calls itself, mid-reasoning, when it decides it actually needs them. The difference isn't just architectural elegance — we benchmarked it. The tool-calling version used meaningfully fewer tokens per response on average, because the model only reaches for memory when a turn genuinely warrants it, instead of every turn paying the cost of a full context injection regardless of relevance.

**What we'd tell someone starting the same track**

Build the forgetting mechanism first, not last. It's tempting to get accumulation working, demo it, and treat decay as a stretch goal — but "timely forgetting" is one of the three things this track explicitly asks for, and it's the piece almost no memory-agent demo actually has. If you only have time for one hard thing, make it that one.

---

*Volta Memory is open source — the memory engine, benchmark dataset, and three reference examples (including one on a different LLM provider entirely, proving the architecture isn't Qwen-specific) are all available in the repository linked below.*

[Repo link] · [Live demo] · [BENCHMARKS.md]
