# Paperly — Enterprise Document Intelligence & Conversational RAG

Paperly is a production-grade Retrieval-Augmented Generation (RAG) platform built for enterprise use. It allows teams to securely upload internal documents (PDF, DOCX) and converse with them using an advanced, context-aware AI architecture. 

Built with **FastAPI (Python)**, **React**, **Qdrant**, and powered by **Groq** and **Cohere**, Paperly is designed for extreme performance, hallucination-free factual recall, and deep conversational memory.

---

## 🌟 Key Enterprise Features

### 1. 3-Level Conversational Memory Architecture
Unlike basic chatbots that blindly pass the last 5 messages, Paperly implements a highly engineered 3-tier memory system:
*   **Level 1 (Short-term Buffer):** Keeps a strict sliding window of the last 3 turns to handle immediate follow-up pronouns natively without blowing up the context window.
*   **Level 2 (Semantic Vector History):** A dedicated `chat_memory` Qdrant collection silently embeds and stores every Q&A interaction. When you ask a new question, Paperly runs a vector search across your *entire past history* to seamlessly recall older topics.
*   **Level 3 (Session State Summarization):** A background LLM asynchronously runs every 5 turns, dynamically synthesizing a "Session Summary State" (user intent, key entities) that is injected into the system prompt to maintain long-term directional context.

### 2. Multi-Stage Hybrid Retrieval
*   **Vector Search:** Powered by Cohere's `embed-english-v3.0` (1024 dims).
*   **Sparse/BM25 Search:** Custom in-memory inverted index for exact keyword matching.
*   **Reciprocal Rank Fusion (RRF):** Intelligently merges dense and sparse results.
*   **Cross-Encoder Reranking:** Re-ranks the top fused results using `bge-reranker-v2-m3` to guarantee maximum context relevance.

### 3. Data Integrity & Management
*   **Multi-tenant Isolation:** All documents, queries, and vector points are hard-filtered by `workspace_id`.
*   **Soft Deletion:** Safely soft-delete chat sessions with custom UI confirmation dialogs to maintain database integrity while cleaning up the workspace.
*   **Missing Knowledge Gap Detection:** Periodically clusters unanswered questions using K-Means to suggest new knowledge base articles to internal teams.
*   **RAGAS Evaluation Dashboard:** Built-in AI evaluation metrics measuring *Faithfulness* and *Relevancy* of the system's answers.

---

## 🛠 Tech Stack

*   **Frontend:** React 19, React Router v7, Lucide Icons, Vanilla CSS Modules
*   **Backend:** FastAPI, SQLAlchemy (Async), Uvicorn
*   **Database:** MySQL (Relational data, User auth, Chat history traces)
*   **Vector Database:** Qdrant (Local SQLite mode or Docker-hosted)
*   **LLM Inference:** Groq API (`llama-3.3-70b-versatile` for ultra-low latency streaming)
*   **Embeddings:** Cohere API (`embed-english-v3.0`)
*   **Reranker:** Local BGE Reranker via `FlagEmbedding`

---

## 🚀 Running Locally (Development Mode)

If you want to run the project locally without full Docker Compose (using XAMPP for MySQL or local SQLite for vectors), follow these steps:

### 1. Database Setup (MySQL via XAMPP)
1. Open XAMPP Control Panel and start **MySQL**.
2. Open phpMyAdmin at `http://localhost/phpmyadmin`.
3. Create a database named `paperly`.

### 2. Backend Setup
Paperly automatically runs Qdrant via a local SQLite file if the `QDRANT_URL` points to a local directory, saving you from running extra Docker containers during development.

1. Navigate to the `backend/` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   source venv/bin/activate  # Mac/Linux
   ```
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file in `backend/`:
   ```env
   # .env
   MYSQL_URL=mysql+aiomysql://root:@localhost:3306/paperly
   QDRANT_URL=local_qdrant_storage  # Uses SQLite engine for vectors
   GROQ_API_KEY=your_groq_api_key
   COHERE_API_KEY=your_cohere_api_key
   JWT_SECRET=super_secret_key_development_only
   ```
5. Apply database schema migrations:
   ```bash
   python fix_schema.py
   ```
6. Run the server: 
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`
3. Start the Vite dev server: `npm run dev`
4. Open `http://localhost:5173` in your browser.

---

## 🌍 Production Deployment (Docker Compose)

For production, the entire stack is containerized, utilizing a dedicated Qdrant instance.

1. Create a `.env` file in the root directory (use `.env.example` as a template).
2. Ensure your host machine has MySQL 8.0 running.
3. Build and start the services:
   ```bash
   docker-compose up --build -d
   ```
4. Access the application at your server IP (served dynamically by Nginx).

---

## 📄 API Documentation

FastAPI automatically generates comprehensive Swagger documentation.
Once the backend is running, navigate to: `http://localhost:8000/docs` to view and test all endpoints including document ingestion, hybrid search traces, and streaming SSE chat routes.
