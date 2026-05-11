# Paperly — Enterprise Document Intelligence Assistant

Paperly is a production-grade Retrieval-Augmented Generation (RAG) backend and React frontend built for internal enterprise use. It allows teams to upload internal PDFs and converse with them securely.

## Features
- **Multi-tenant Architecture:** Data is isolated per workspace.
- **Hybrid Search:** Combines dense vectors (Qdrant + Gemini text-embedding-004) with sparse search (in-memory BM25) using Reciprocal Rank Fusion.
- **RAGAS Evaluation:** Automated quality assessment (faithfulness, relevancy) of the system's answers.
- **Knowledge Gap Detection:** Automatically clusters unanswered queries using k-means and suggests new document titles to fill gaps.
- **Streaming Responses:** Token-by-token streaming via SSE for low-latency perceived generation.

---

## Running Locally (XAMPP + Local Environment)

If you want to run the project locally without full Docker Compose (using XAMPP for MySQL), follow these steps:

### 1. Database Setup (XAMPP)
1. Open XAMPP Control Panel and start **MySQL**.
2. Open phpMyAdmin (or any MySQL client) at `http://localhost/phpmyadmin`.
3. Create a database named `paperly`.
4. (Optional) Create a dedicated user, or just use the default `root` user with no password.

### 2. Qdrant Setup (Docker)
While you run Python and Node locally, Qdrant needs to run in Docker. Open a terminal and run:
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

### 3. Backend Setup
Open a terminal in the `backend` directory:
1. Create a virtual environment: `python -m venv venv`
2. Activate it:
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables. Create `.env` in `backend/`:
   ```env
   # .env
   MYSQL_URL=mysql+aiomysql://root:@localhost:3306/paperly
   QDRANT_URL=http://localhost:6333
   GEMINI_API_KEY=your_gemini_api_key
   COHERE_API_KEY=your_cohere_api_key
   JWT_SECRET=super_secret_key_change_in_production
   ```
5. Run the server: `uvicorn app.main:app --reload --port 8000`

### 4. Frontend Setup
Open a new terminal in the `frontend` directory:
1. Install dependencies: `npm install`
2. Start the Vite dev server: `npm run dev`
3. Open `http://localhost:5173` in your browser.

---

## Production Deployment (Docker Compose)

For production, the entire stack is containerized.

1. Create a `.env` file in the root directory (use `.env.example` as a template).
2. Ensure your host machine has MySQL 8.0 running (the `docker-compose.yml` routes `host.docker.internal` to the host's MySQL).
3. Build and start the services:
   ```bash
   docker-compose up --build -d
   ```
4. Access the application at `http://<your-vps-ip>` (served by Nginx).
