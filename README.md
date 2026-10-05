# RAG Knowledge Assistant

> Ask questions over your own documents. Upload PDFs, get answers **with exact citations**, and verify facts with **LLM-as-judge faithfulness scoring**.

### 🎥 Demo Video
<video src="https://github.com/user-attachments/assets/f00abfa3-593d-454c-9e5a-e1522acf048f" controls="controls" muted="muted" playsinline="playsinline"></video>


---

## 📖 What It Does
The **RAG Knowledge Assistant** is an end-to-end Retrieval-Augmented Generation (RAG) platform. It allows users to securely upload PDF documents into their own personal namespaces, ask complex questions across one or multiple documents, and receive highly accurate, grounded answers. 

Unlike standard AI chat interfaces, this assistant prioritizes **truthfulness and traceability**. Every claim the LLM makes is backed by a specific citation, and a secondary "Judge LLM" evaluates the faithfulness of the answer against the retrieved context to prevent hallucinations.

## ✨ Key Features
- **Upload & Query PDFs**: Process and chunk PDF documents to make them instantly searchable.
- **Precision Citations**: Responses include in-line citations (e.g., `[1]`, `[2]`) linking back to the exact source passages.
- **LLM-as-Judge Faithfulness Scoring**: Every generated answer is evaluated and scored for faithfulness. Visual badges instantly indicate if a claim is fully supported by the underlying document.
- **Multi-Document Comparison**: Select two documents side-by-side and ask comparative questions (e.g., "How do these documents differ on topic X?").
- **Secure Per-User Namespaces**: JWT-based authentication ensures users can only access, manage, and query their own uploaded documents.
- **Premium UI**: A sleek, responsive React frontend featuring a glassmorphic design and a built-in citation viewer.

## 🛠️ Tech Stack
- **Frontend**: React, Vite, Modern CSS
- **Backend**: Python, FastAPI
- **Database / Vector Store**: PostgreSQL with the `pgvector` extension
- **Embeddings & Reranking**: `all-MiniLM-L6-v2` (local embeddings), `ms-marco-MiniLM-L-6-v2` (cross-encoder reranker)
- **LLM**: Gemini or Groq

## 🚀 Getting Started

### 1. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
*Make sure to add your `GEMINI_API_KEY` (or `GROQ_API_KEY` if using Groq) and set a secure `JWT_SECRET`.*

### 2. Start the Backend & Database
Use Docker Compose to spin up the PostgreSQL database and FastAPI backend:
```bash
docker compose up --build
```

### 3. Start the Frontend
In a new terminal, install dependencies and run the React development server:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173` in your browser to register an account, log in, and start chatting with your PDFs!

## 🧠 Architecture Pipeline

1. **Ingestion**: PDF → Extracted Text → Chunks → Vector Embeddings (`all-MiniLM-L6-v2`) → Saved to `pgvector`.
2. **Retrieval**: User Query → Embedding → Vector Similarity Search (Top-N chunks) → Cross-Encoder Reranking (Top-K chunks).
3. **Generation**: Top-K chunks + Query → LLM Prompt → Grounded Answer with Citations.
4. **Evaluation**: Answer + Source Chunks → Judge LLM Prompt → Faithfulness Score & Verdict.
