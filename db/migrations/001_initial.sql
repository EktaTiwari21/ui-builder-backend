-- Initial schema setup for Autonomous UI Builder Agent - Backend
-- Covers profiles, projects, generations, and templates tables.

-- Create profiles table (references Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  name TEXT,
  subscription_plan TEXT DEFAULT 'free',
  generations_today INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  generated_code TEXT,
  preview_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create generations table for audit/metrics logging
CREATE TABLE IF NOT EXISTS generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  ai_model TEXT,
  prompt_tokens INT,
  response_tokens INT,
  generation_status TEXT DEFAULT 'pending',
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create templates table
CREATE TABLE IF NOT EXISTS templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT,
  template_name TEXT,
  metadata JSONB
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_project_id ON generations(project_id);

-- GIN index for full-text search on prompt
CREATE INDEX IF NOT EXISTS idx_projects_prompt_fts ON projects USING GIN (to_tsvector('english', prompt));
