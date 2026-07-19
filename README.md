# Volta Memory Engine 🧠⚡

<div align="center">
  <h3><strong>Qwen Cloud Global AI Hackathon | Track 1: MemoryAgent</strong></h3>
  <p>A serverless, persistent memory engine that gives AI companions compounding, long-term context.</p>
</div>

---

## 🌟 The "Wow" Factor: Premium Solar Concierge
Volta Memory isn't just a backend API—it's a fully realized product. To demonstrate the power of our memory engine, we built a **Premium Solar Concierge**.

* **Live Force-Graph Memory:** Navigate to the `/memory` route to see the AI's brain in real-time. Memories are rendered as glowing, physics-based nodes. Watch as high-confidence memories burn bright, while outdated or contradicted facts physically shrink and decay over time.
* **Push-to-Talk Voice Interface:** A zero-latency, highly polished voice interface allows you to speak naturally with Volta, while it reads back responses using premium browser-native TTS.
* **Compounding Intelligence:** Talk to Volta across multiple sessions. Without being reminded, it will recall your roof size, budget constraints, and energy goals from days prior.

## 🌐 Deployed Live Demos

* **Live Concierge Web App:** [https://volta-memory-frontend-static.oss-ap-southeast-1.aliyuncs.com/index.html](https://volta-memory-frontend-static.oss-ap-southeast-1.aliyuncs.com/index.html)
* **Live Memory Engine API (FC):** [https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/health](https://volta-m-backend-mlutvrvuqy.ap-southeast-1.fcapp.run/health)

## 🏗️ The "How": Engineering & Architecture
Volta is built entirely on a cutting-edge, serverless, cloud-native stack designed for infinite scale and zero idle costs.

* **Compute:** Alibaba Cloud Function Compute 3.0 (FC3.0) running a FastAPI backend.
* **Database:** Alibaba ApsaraDB RDS Serverless (PostgreSQL) leveraging `pgvector` for semantic similarity search.
* **Intelligence:** Qwen LLMs integrated via Alibaba DashScope.
* **Frontend:** Next.js 14 Static Export hosted on Alibaba Cloud OSS.
* **Standards:** Full **Model Context Protocol (MCP)** integration, exposing the memory engine as standard tools for any compliant LLM.

## 📊 Rigorous Benchmarks (132-Scenario Sweep)

To prove the efficacy of our memory architecture, we benchmarked Volta against three industry-standard baselines across **132 chronological evaluation scenarios**:

| System | Recall Accuracy | Correction Accuracy | Forgetting Accuracy | Downstream Quality | Online Latency P50 (ms) | Online Cost Avg ($) | Sample runs |
|---|---|---|---|---|---|---|---|
| **A_no_memory** | 0.1364 (9/66) | 0.0000 (0/6) | 0.7917 (19/24) | 0.3457 (28/81) | 5500 | $0.001542 | 33 |
| **B_full_context** | 1.0000 (66/66) | 0.0000 (0/6) | 0.2500 (6/24) | 0.8519 (69/81) | 6856 | $0.001813 | 33 |
| **C_naive_rag** | 0.9091 (60/66) | 0.0000 (0/6) | 0.1667 (4/24) | 0.7901 (64/81) | 10573 | $0.001639 | 33 |
| **D_volta_memory** | 0.8333 (55/66) | **0.5000 (3/6)** | **0.6667 (16/24)** | 0.8148 (66/81) | 9338 | $0.002010 | 33 |

* **Active Correction**: Volta is the **only** memory architecture capable of overwriting outdated facts with corrections downstream, achieving **50% Downstream Correction Accuracy** and **100% DB Superseded Accuracy**.
* **Selective Forgetting**: Volta beats all memory-capable baselines at decay-based forgetting (**66.7%** vs. 25% for full-context and 16.7% for naive RAG) by excluding low-importance/decayed memories under a token budget.
* **Recall & Quality**: Volta maintains competitive downstream response quality (**0.8148**) compared to full-history (**0.8519**) while consuming **34% fewer tokens**.

For the detailed logs and methodology, see [BENCHMARKS.md](BENCHMARKS.md).

## 📚 Deep Dive Documentation
We have prepared a comprehensive 16-document suite covering every aspect of this project—from the database schema to our product roadmap. 

**Start Here:**
* 📖 [Master Index & Table of Contents](docs/00_Master_Index.md)
* 🚀 [Demo Script (3-Session Scenario)](docs/06_Demo_Script.md)
* 📐 [Memory System Design & Decay Logic](docs/03_Memory_System_Design.md)
* 🗺️ [Architecture Diagrams](docs/15_Architecture_Diagram_Spec.md)
* 💡 [FAQ & One-Page Pitch](docs/11_FAQ_and_One_Pager.md)

*(See the `docs/` directory for PRDs, Security, Roadmap, and more).*

## 🚀 Getting Started Locally

### 1. Backend (FastAPI + Memory Engine)
```bash
cd backend
python3 -m pip install -e .
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (Next.js Solar Concierge)
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000 to interact with Volta
```

---
*Built with ❤️ for the Qwen Cloud Global AI Hackathon (June 2026).*
