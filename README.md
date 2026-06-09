# Autonomous UI Builder Agent — Backend

A FastAPI backend that receives user prompts from the frontend, orchestrates AI agents (Gemini for planning, OpenAI for code generation), validates output, and streams React + Tailwind component code back to the client using Server-Sent Events (SSE).

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI Orchestration**: LangGraph + LangChain
- **Planning Agent**: Google Gemini API (`gemini-1.5-pro`)
- **Code Generation**: OpenAI API (`gpt-4o`)
- **Database / Auth**: Supabase (PostgreSQL, Supabase Auth)
- **Streaming**: Server-Sent Events (SSE) via `sse-starlette`
- **Testing**: Pytest + pytest-asyncio
- **Deploy**: Railway / Docker

---

## Local Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/EktaTiwari21/ui-builder-backend.git
cd ui-builder-backend
```

### 2. Create and Activate a Virtual Environment
**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```
**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# AI APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# App
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
SECRET_KEY=your-secret-key
```

### 5. Run the Server Locally
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
The server will start on `http://127.0.0.1:8000`.

---

## Running Tests

Ensure your virtual environment is active and run pytest:
```bash
# Run the complete test suite
python -m pytest --tb=short
```

---

## API Endpoints

All endpoints except `/health` require a valid JWT token in the `Authorization` header (`Bearer <token>`).

### 1. `POST /generate-ui`
Generates React/Tailwind component code from a text prompt as an SSE stream.
- **Rate Limit**: Free users: 10/day, Premium: 100/day.
- **Request Body**:
  ```json
  {
    "prompt": "Build a SaaS pricing page with 3 tiers",
    "style": "minimal",
    "framework": "react-tailwind"
  }
  ```
- **Response**: Server-Sent Events (SSE) stream.

### 2. `POST /improve-ui`
Improves existing generated UI based on feedback instructions.
- **Request Body**:
  ```json
  {
    "project_id": "uuid",
    "instruction": "Make the hero section larger"
  }
  ```

### 3. `GET /projects`
Retrieve all projects for the authenticated user.
- **Response**: List of project records.

### 4. `GET /project/{id}`
Retrieve details of a single project by ID.
- **Response**: Detailed project metadata and code.

### 5. `DELETE /project/{id}`
Delete a project by ID.
- **Response**: `{"success": true}`

### 6. `POST /export-project`
Export the project code and return a download URL.
- **Request Body**:
  ```json
  {
    "project_id": "uuid"
  }
  ```

### 7. `GET /health`
System health check. No authentication required.

---

## Deployment & Containerisation

### Docker
A `Dockerfile` is provided for containerized deployments:
```bash
docker build -t ui-builder-backend .
docker run -p 8000:8000 --env-file .env ui-builder-backend
```

### Railway
This project is configured for deployment on Railway using the [railway.toml](file:///e:/ui-builder-backend/railway.toml) file. Deployment triggers automatically on push to the `main` branch.