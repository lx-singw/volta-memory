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

## 🏗️ The "How": Engineering & Architecture
Volta is built entirely on a cutting-edge, serverless, cloud-native stack designed for infinite scale and zero idle costs.

* **Compute:** Alibaba Cloud Function Compute 3.0 (FC3.0) running a FastAPI backend.
* **Database:** Alibaba ApsaraDB RDS Serverless (PostgreSQL) leveraging `pgvector` for semantic similarity search.
* **Intelligence:** Qwen LLMs integrated via Alibaba DashScope.
* **Frontend:** Next.js 14 Static Export hosted on Alibaba Cloud OSS.
* **Standards:** Full **Model Context Protocol (MCP)** integration, exposing the memory engine as standard tools for any compliant LLM.

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
