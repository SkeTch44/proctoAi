-- ============================================================
-- ProctoAI Postgres bootstrap
-- Runs once on a fresh Postgres volume (see docker-compose.yml).
-- ============================================================

-- pgvector for RAG (kills the need for a separate vector DB early)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Per-service logical schemas. Single physical DB for now; each
-- service owns one schema and cannot cross-join into others.
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS exams;
CREATE SCHEMA IF NOT EXISTS questions;
CREATE SCHEMA IF NOT EXISTS coding;
CREATE SCHEMA IF NOT EXISTS proctoring;
CREATE SCHEMA IF NOT EXISTS grading;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS rag;

-- Default the app user's search_path so the baseline Alembic run
-- (which creates tables in `public`) continues to work during the
-- dual-write window. Service-specific migrations will target their
-- own schemas from P2 onwards.
ALTER DATABASE proctoai SET search_path TO public, auth, exams, questions, coding, proctoring, grading, notifications, rag;
