from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.config import settings
from app.api import generate, improve, projects, export

app = FastAPI(
    title="Autonomous UI Builder Agent - Backend",
    description="FastAPI backend for orchestrating UI planning and generation agents.",
    version="1.0.0"
)

# Configure CORS
# Allow both FRONTEND_URL from settings and localhost:3000 for local development
origins = list({settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/", response_class=HTMLResponse, tags=["System"])
async def root():
    """Welcome page with system status and API details."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous UI Builder - Backend API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.15);
            --secondary: #3b82f6;
            --secondary-glow: rgba(59, 130, 246, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            position: relative;
        }

        body::before {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
            top: -10%;
            left: -10%;
            z-index: 0;
            pointer-events: none;
        }

        body::after {
            content: '';
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, var(--secondary-glow) 0%, transparent 70%);
            bottom: -10%;
            right: -10%;
            z-index: 0;
            pointer-events: none;
        }

        .container {
            width: 100%;
            max-width: 800px;
            padding: 2rem;
            z-index: 1;
            animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            text-align: center;
        }

        .logo-container {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 20px;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 20px rgba(139, 92, 246, 0.4);
            font-size: 2.5rem;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 2.2rem;
            background: linear-gradient(to right, #ffffff, #a78bfa, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-bottom: 2rem;
            font-weight: 300;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--accent);
            padding: 0.5rem 1.25rem;
            border-radius: 100px;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 2.5rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--accent);
            position: relative;
        }

        .status-dot::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background-color: var(--accent);
            border-radius: 50%;
            top: 0;
            left: 0;
            animation: pulse 1.8s infinite ease-in-out;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
            text-align: left;
        }

        .grid-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 1.25rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .grid-item:hover {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(139, 92, 246, 0.3);
            transform: translateY(-2px);
        }

        .grid-item-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }

        .grid-item-value {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main);
        }

        .btn-group {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.85rem 2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.95rem;
            text-decoration: none;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #7c3aed);
            color: white;
            border: none;
            box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
        }

        .btn-primary:hover {
            background: linear-gradient(135deg, #9333ea, #6d28d9);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }

        .footer {
            margin-top: 3rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes pulse {
            0% {
                transform: scale(1);
                opacity: 0.8;
            }
            100% {
                transform: scale(2.4);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="logo-container">🧠</div>
            <h1>Autonomous UI Builder</h1>
            <p class="subtitle">API Orchestration & Generation Engine</p>
            
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>API Operational</span>
            </div>

            <div class="grid">
                <div class="grid-item">
                    <div class="grid-item-title">Framework</div>
                    <div class="grid-item-value">FastAPI ⚡</div>
                </div>
                <div class="grid-item">
                    <div class="grid-item-title">API Version</div>
                    <div class="grid-item-value">1.0.0</div>
                </div>
                <div class="grid-item">
                    <div class="grid-item-title">Environment</div>
                    <div class="grid-item-value">{environment}</div>
                </div>
                <div class="grid-item">
                    <div class="grid-item-title">CORS Status</div>
                    <div class="grid-item-value">Configured 🔒</div>
                </div>
            </div>

            <div class="btn-group">
                <a href="/docs" class="btn btn-primary">Interactive API Docs</a>
                <a href="/health" class="btn btn-secondary">Check Health Status</a>
            </div>
            
            <div class="footer">
                Developed by Ekta Tiwari &bull; Phase 2 - Active Development
            </div>
        </div>
    </div>
</body>
</html>""".replace("{environment}", settings.environment.capitalize())
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check route to verify that the service is running."""
    return {
        "status": "ok",
        "environment": settings.environment
    }

# Register routers
app.include_router(generate.router)
app.include_router(improve.router)
app.include_router(projects.router)
app.include_router(export.router)
