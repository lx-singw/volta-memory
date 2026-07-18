# Volta Memory — Architecture Diagram Specification
**Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent**
**Satisfies the submission requirement: "Include an Architecture Diagram showing a clear visual representation of your system"**

---

## Table of Contents
- [1. Purpose](#1-purpose)
- [2. Full System Diagram (Mermaid Source)](#2-full-system-diagram-mermaid-source)
- [3. Memory Pipeline Detail Diagram](#3-memory-pipeline-detail-diagram)
- [4. Deployment Topology Diagram](#4-deployment-topology-diagram)
- [5. How to Render These](#5-how-to-render-these)

---

## 1. Purpose

The submission requirement asks specifically for a diagram showing "how Qwen Cloud connects to your backend, database, and frontend." This document provides three diagrams at different levels of detail, all as Mermaid source — renderable directly on GitHub (which natively supports Mermaid in markdown), so the architecture diagram requirement is satisfied by this file alone appearing in the repository, with no separate image-export step required, though a rendered PNG/SVG export should also be generated and embedded in the main README for anyone viewing outside GitHub's renderer.

---

## 2. Full System Diagram (Mermaid Source)

```mermaid
graph TB
    subgraph Frontend["Frontend — Next.js"]
        UI[Chat Interface]
        MTV[Memory Transparency View]
        SM[StreamingMessage Component]
    end

    subgraph Backend["Backend — FastAPI, Alibaba-hosted"]
        API[API Routes]
        SESSION[Session Manager]
        MEM[Memory Engine]
        MCP[MCP Server]
    end

    subgraph MemoryEngine["Memory Engine Detail"]
        STORE[Typed Memory Store]
        DECAY[Decay + Stability Model]
        IMPORTANCE[Self-Scored Importance]
        RETRIEVAL[Retrieval Ranking]
        HYBRID[Hybrid Embedding Fallback]
        PLAUSIBILITY[Plausibility Gate]
        CONSOLIDATION[Consolidation Cycle]
    end

    subgraph QwenCloud["Qwen Cloud"]
        CHAT[Chat Completion]
        EMBED[Embeddings]
        TOOLCALL[Native Tool Calling]
    end

    subgraph DB["Alibaba RDS — Postgres + pgvector"]
        MEMTABLE[(memories)]
        CONVTABLE[(conversations)]
        MSGTABLE[(messages)]
        POPTABLE[(population_patterns)]
    end

    UI --> API
    SM --> API
    MTV --> API
    API --> SESSION
    SESSION --> MEM
    MEM --> STORE
    MEM --> DECAY
    MEM --> IMPORTANCE
    MEM --> RETRIEVAL
    MEM --> HYBRID
    MEM --> PLAUSIBILITY
    MEM --> CONSOLIDATION
    STORE --> MEMTABLE
    SESSION --> CONVTABLE
    SESSION --> MSGTABLE
    HYBRID --> POPTABLE
    API --> MCP
    MCP -->|tool calls| CHAT
    MCP -->|embedding requests| EMBED
    SESSION -->|complete/complete_stream| CHAT
    SESSION -->|native tool calling| TOOLCALL
    IMPORTANCE -->|scoring calls| CHAT
    PLAUSIBILITY -->|plausibility check| CHAT
    HYBRID -->|embed transcript chunks| EMBED
```

---

## 3. Memory Pipeline Detail Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant V as Volta (Qwen)
    participant MCP as MCP Server
    participant M as Memory Store
    participant D as Database

    U->>V: sends message
    V->>MCP: check_memory_confidence(topic)
    MCP->>M: query effective_confidence + importance
    M->>D: read memories WHERE entity_id
    D-->>M: rows
    M-->>MCP: {confidence, importance, action}
    MCP-->>V: recommended_action
    alt action == CLARIFY
        V->>U: asks clarifying question
    else action == STATE
        V->>MCP: get_memory_context(query)
        MCP->>M: rank + pack to token budget
        M-->>MCP: packed memories
        MCP-->>V: context
        V->>U: confident, memory-informed response
    end
    U->>V: (session ends)
    V->>M: extract_and_write(transcript)
    M->>M: plausibility check
    M->>M: contradiction check
    M->>D: write memory row(s)
```

---

## 4. Deployment Topology Diagram

```mermaid
graph LR
    subgraph Public["Public Internet"]
        Judge[Judge / Public Visitor]
    end

    subgraph Alibaba["Alibaba Cloud"]
        subgraph ECS["ECS Instance"]
            App[FastAPI + MCP Server]
        end
        RDS[(RDS Postgres + pgvector)]
    end

    subgraph External["External Services"]
        Qwen[Qwen Cloud API]
    end

    Judge -->|HTTPS| App
    App -->|internal network| RDS
    App -->|API calls| Qwen
```

---

## 5. How to Render These

- GitHub renders Mermaid blocks natively in any `.md` file — this document, viewed on GitHub, already displays all three diagrams without additional tooling
- For the main repository README and the Devpost submission (which may not support live Mermaid rendering), export static PNG/SVG versions using the Mermaid CLI (`mmdc`) or the Mermaid Live Editor, and embed the exported image alongside a link back to this document's live-rendered source
- The deployment proof recording (Document 07's compliance checklist) should visually reference the topology diagram (Section 4) when narrating which Alibaba Cloud components are actually running, so a judge can map the live recording directly onto the diagram
