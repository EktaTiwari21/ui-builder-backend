# AGENTS.md — Autonomous UI Builder Agent

> This file is automatically loaded by Antigravity 2.0, Claude Code, and compatible AI agents at session start.
> It gives the agent full project context so every session starts informed — no repeated onboarding.

---

## Project identity

| Field | Value |
|---|---|
| Project name | Autonomous UI Builder Agent |
| Tagline | "Describe your app idea. Let AI design and generate your frontend instantly." |
| Author | Ekta Tiwari |
| PRD version | 1.0 — May 24, 2026 |
| Current phase | Phase 1 — Frontend MVP |
| Status | Active development |

---

## What this product does

An AI-powered platform that transforms natural language prompts into production-ready React/Tailwind frontends.

The user types a description → AI agents plan the UI architecture → generate component code → render a live preview → user refines or exports.

**Core loop:** Prompt → Plan → Generate → Preview → Refine → Export

---

## Repository layout

This project is split across two independent repos. Never mix concerns between them.

```
ui-builder-frontend/    ← You are working here in Phase 1
ui-builder-backend/     ← Phase 2 (FastAPI + AI orchestrator)
```

### Frontend repo — `ui-builder-frontend`

**Framework:** Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS  
**UI library:** shadcn/ui · Lucide icons · Framer Motion  
**State:** Zustand (global) · React Context (UI-scoped)  
**Testing:** Vitest · React Testing Library · Playwright (E2E)  
**Deploy:** Vercel

#### Folder structure

```
ui-builder-frontend/
├── app/                        # Next.js App Router pages
│   ├── layout.tsx              # Root layout (fonts, providers)
│   ├── page.tsx                # Landing / redirect
│   ├── dashboard/
│   │   └── page.tsx            # Project list dashboard
│   ├── workspace/
│   │   ├── page.tsx            # New project workspace
│   │   └── [projectId]/
│   │       └── page.tsx        # Existing project workspace
│   ├── projects/
│   │   └── page.tsx            # Project management
│   └── settings/
│       └── page.tsx            # User settings
│
├── components/
│   ├── ui/                     # shadcn/ui primitives (auto-generated, do not edit)
│   ├── workspace/
│   │   ├── PromptInput.tsx     # Prompt textarea + submit button
│   │   ├── ChatRefinement.tsx  # Chat thread for iterative refinement
│   │   └── WorkspaceLayout.tsx # Two-panel split layout
│   ├── preview/
│   │   ├── LivePreview.tsx     # Iframe-based live renderer
│   │   ├── CodeEditor.tsx      # Generated code viewer (read-only + copy)
│   │   └── PreviewToolbar.tsx  # Responsive toggle, refresh, export
│   ├── dashboard/
│   │   ├── ProjectCard.tsx     # Project thumbnail card
│   │   ├── ProjectGrid.tsx     # Responsive grid of cards
│   │   └── EmptyState.tsx      # Illustration + CTA for no projects
│   ├── editor/
│   │   ├── ComponentTree.tsx   # Generated component hierarchy
│   │   └── ThemePanel.tsx      # Color/font customization
│   └── common/
│       ├── Navbar.tsx
│       ├── Sidebar.tsx
│       └── LoadingSpinner.tsx
│
├── lib/
│   ├── api/
│   │   ├── client.ts           # Axios/fetch wrapper (points to backend)
│   │   ├── mock.ts             # Mock responses — used in Phase 1 only
│   │   └── endpoints.ts        # All API endpoint constants
│   ├── ai/
│   │   └── stream.ts           # SSE streaming handler (Phase 3)
│   ├── store/
│   │   ├── useProjectStore.ts  # Zustand: project CRUD + active project
│   │   ├── useGenerationStore.ts # Zustand: generation status + results
│   │   └── useUIStore.ts       # Zustand: sidebar, panels, view modes
│   └── utils/
│       ├── codeFormatter.ts    # Prettier wrapper for generated code
│       └── exportProject.ts    # Zip + download helper
│
├── hooks/
│   ├── useGenerate.ts          # Trigger generation + poll status
│   ├── useProject.ts           # Load / save / delete project
│   └── useResponsive.ts        # Breakpoint helpers
│
├── types/
│   ├── project.ts              # Project, Generation, Component types
│   └── api.ts                  # Request/response shapes
│
├── public/
├── tailwind.config.ts
├── next.config.ts
└── tsconfig.json
```

### Backend repo — `ui-builder-backend`

**Framework:** FastAPI · Python 3.11+  
**Database:** PostgreSQL via Supabase  
**Auth:** Supabase Auth (JWT)  
**AI:** Gemini API (planning) · OpenAI API (code generation)  
**Testing:** Pytest  
**Deploy:** Railway or Render

#### Folder structure (Phase 2 — do not create yet)

```
ui-builder-backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── generate.py         # POST /generate-ui
│   │   ├── projects.py         # GET/DELETE /projects, /project/:id
│   │   ├── export.py           # POST /export-project
│   │   └── improve.py          # POST /improve-ui
│   ├── services/
│   │   ├── orchestrator.py     # AI agent orchestration (LangGraph)
│   │   ├── planner.py          # UI architecture planning (Gemini)
│   │   ├── generator.py        # Component code generation (OpenAI)
│   │   └── validator.py        # Code linting + safety checks
│   ├── models/
│   │   ├── user.py
│   │   ├── project.py
│   │   └── generation.py
│   └── db/
│       └── supabase.py
└── tests/
```

---

## Database schema (Supabase / PostgreSQL)

```sql
-- Users
users (id UUID PK, name TEXT, email TEXT UNIQUE, subscription_plan TEXT, created_at TIMESTAMP)

-- Projects
projects (id UUID PK, user_id UUID FK→users, title TEXT, prompt TEXT,
          generated_code TEXT, preview_url TEXT, created_at TIMESTAMP)

-- Generations (audit log per AI call)
generations (id UUID PK, project_id UUID FK→projects, ai_model TEXT,
             prompt_tokens INT, response_tokens INT,
             generation_status TEXT, latency INT)

-- Templates
templates (id UUID PK, category TEXT, template_name TEXT, metadata JSONB)
```

**Indexes:** `user_id`, `created_at`, full-text on `prompt`  
**Relationships:** one user → many projects · one project → many generations

---

## API contract (backend — Phase 2)

| Method | Path | Purpose |
|---|---|---|
| POST | `/generate-ui` | Generate UI from prompt |
| POST | `/improve-ui` | Improve existing generated UI |
| POST | `/export-project` | Export codebase as zip |
| GET | `/projects` | List user's projects |
| GET | `/project/:id` | Single project details |
| DELETE | `/project/:id` | Delete project |

All requests: JSON body  
All responses: structured JSON  
Auth: `Authorization: Bearer <jwt>`  
Rate limiting: free tier = 10 generations/day · premium = 100/day

---

## AI agent pipeline

```
User Prompt
  → Prompt Parser        (normalize, sanitize, extract intent + style)
  → UI Planner Agent     (Gemini — layout architecture, component list)
  → Component Generator  (OpenAI — React/Tailwind code, structured JSON)
  → Validator            (lint, safety, accessibility check)
  → Accessibility Agent  (ARIA, contrast, keyboard nav)
  → Final Output         (streamed to frontend via SSE)
```

**Gemini API** — large-context reasoning, UI planning, architecture suggestions  
**OpenAI API** — frontend code generation, structured JSON output, conversational refinement  
**LangChain / LangGraph** — multi-agent orchestration, retry + fallback routing

---

## Tech stack quick-reference

| Layer | Technology |
|---|---|
| Frontend framework | Next.js 15 · App Router · React 19 · TypeScript |
| Styling | Tailwind CSS · shadcn/ui · Framer Motion |
| State management | Zustand · React Context |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL via Supabase |
| Auth | Supabase Auth · JWT |
| AI — planning | Gemini API |
| AI — code gen | OpenAI API |
| Agent orchestration | LangChain · LangGraph |
| CI/CD | GitHub Actions |
| Frontend deploy | Vercel |
| Backend deploy | Railway or Render |
| Monitoring | Sentry · PostHog |
| E2E testing | Playwright |

---

## Current phase rules (Phase 1 — Frontend)

The agent must follow these constraints until Phase 3 begins:

1. **No real backend calls.** All API interactions must go through `lib/api/mock.ts`. The mock must return realistic-looking generated component code.
2. **Light theme only.** Do not implement dark mode. No `dark:` Tailwind variants. No theme toggle. This will be added in a future phase.
3. **No authentication UI yet.** Assume a logged-in user. No sign-in / sign-up pages in Phase 1.
4. **React/Tailwind output only.** Generated code examples in the mock should always be React + Tailwind. No Vue, no plain HTML output yet.
5. **Responsive by default.** Every component must work at mobile (375px), tablet (768px), and desktop (1280px). Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`).
6. **shadcn/ui for all form elements and primitives.** Do not hand-roll buttons, inputs, dialogs, or dropdowns — import from `@/components/ui/`.

---

## Code style and conventions

- **TypeScript strict mode** — no `any`, no implicit returns
- **Named exports** for all components (no default exports except page files)
- **File naming:** PascalCase for components, camelCase for hooks/utils
- **Imports:** absolute paths via `@/` alias (configured in `tsconfig.json`)
- **CSS:** Tailwind utility classes only — no custom CSS files except `globals.css`
- **Comments:** JSDoc on all exported functions and component props
- **Component pattern:**
  ```tsx
  // Always define Props interface above component
  interface PromptInputProps {
    onSubmit: (prompt: string) => void;
    isLoading: boolean;
  }

  export function PromptInput({ onSubmit, isLoading }: PromptInputProps) { ... }
  ```
- **Zustand store pattern:**
  ```ts
  // lib/store/useProjectStore.ts
  interface ProjectStore {
    projects: Project[];
    activeProject: Project | null;
    setActiveProject: (p: Project) => void;
  }
  export const useProjectStore = create<ProjectStore>()(...)
  ```

---

## Performance targets (non-negotiable)

| Metric | Target |
|---|---|
| Initial page load | < 3 seconds |
| AI generation response | < 20 seconds |
| Live preview update | < 1 second |
| Export generation | < 10 seconds |
| Lighthouse accessibility score | > 85 |
| Responsive layout accuracy | > 90% |

---

## Security rules

- Never log prompt content or generated code to the console in production
- All user input must be sanitized before being sent to any API
- API keys must only live in `.env.local` — never hardcoded
- Use `next/headers` and server components for any sensitive reads
- Rate limit all generation endpoints on the backend

---

## What is explicitly out of scope for MVP

Do not build or suggest these — they are deferred to Phase 3+:

- Full backend generation (only frontend code is generated)
- Native mobile app generation
- Real-time collaboration / multiplayer editing
- Offline AI inference
- Advanced animation engine
- Full Figma-to-code conversion
- Enterprise team management
- Dark mode (Phase 2)
- Authentication UI (Phase 2)
- GitHub export (Phase 2)
- Voice prompt support (Phase 2)

---

## Useful prompts to continue work

When you need the agent to continue from a specific point, use these as session starters:

```
# Scaffold a new component
"Create [ComponentName] in components/[folder]/ following the project's TypeScript
and Tailwind conventions. Props should include [list props]."

# Add a new page
"Add a new page at app/[route]/page.tsx. Use the existing Navbar and Sidebar
layout. The page should [describe purpose]."

# Wire mock data
"Update lib/api/mock.ts to return a realistic mock response for [endpoint].
The response shape should match the types in types/project.ts."

# Fix a bug
"Here is the error: [paste error]. The relevant file is [filename].
Find the root cause and fix it without touching other components."

# Write tests
"Write Vitest unit tests for [ComponentName]. Cover: [list cases].
Use React Testing Library. Mock any Zustand stores."
```

---

## Agent behaviour guidelines

- **Always read existing code before writing new code.** Never assume a file doesn't exist.
- **Prefer editing over creating.** If a component partially exists, extend it.
- **One task per session.** Do not refactor unrelated files while implementing a feature.
- **Commit message format:** `feat: add PromptInput component` / `fix: correct Zustand store type` / `chore: update mock API responses`
- **When unsure about scope,** check this file first. If still unclear, ask before writing code.
- **Do not change `tailwind.config.ts`** without an explicit instruction to do so.
- **Do not install new npm packages** without checking if a shadcn/ui primitive or existing dependency already covers the need.
