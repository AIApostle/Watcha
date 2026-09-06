"""
Database initialization script.

Run this against your Supabase project's SQL Editor to create
all required tables and Row Level Security policies.

Usage:
    Copy the SQL below and execute it in Supabase Dashboard > SQL Editor.
    Or run: python -m scripts.init_db (prints the SQL).
"""

INIT_SQL = """
-- ============================================================================
-- TheWatcher — Database Schema
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Profiles ────────────────────────────────────────────────────────────────
-- Extends Supabase auth.users with app-specific settings.

CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    telegram_chat_id TEXT,
    telegram_verified BOOLEAN DEFAULT FALSE,
    polling_interval  INTEGER DEFAULT 15 CHECK (polling_interval IN (5, 15, 30, 60)),
    alert_sensitivity TEXT DEFAULT 'medium' CHECK (alert_sensitivity IN ('all', 'high', 'medium', 'low')),
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Service role can manage all profiles" ON profiles;
CREATE POLICY "Service role can manage all profiles"
    ON profiles FOR ALL
    USING (true)
    WITH CHECK (true);


-- ── Watched Assets ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS watched_assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    asset_symbol    TEXT NOT NULL,
    asset_name      TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (user_id, asset_symbol)
);

ALTER TABLE watched_assets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own assets" ON watched_assets;
CREATE POLICY "Users can view own assets"
    ON watched_assets FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own assets" ON watched_assets;
CREATE POLICY "Users can insert own assets"
    ON watched_assets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own assets" ON watched_assets;
CREATE POLICY "Users can delete own assets"
    ON watched_assets FOR DELETE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all assets" ON watched_assets;
CREATE POLICY "Service role can manage all assets"
    ON watched_assets FOR ALL
    USING (auth.role() = 'service_role');


-- ── Alerts ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    asset_symbol    TEXT,
    alert_type      TEXT NOT NULL CHECK (alert_type IN ('price_move', 'news', 'social', 'composite')),
    severity        TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    title           TEXT NOT NULL,
    body            TEXT,
    ai_analysis     TEXT,
    source_data     JSONB DEFAULT '{}',
    impact_score    INTEGER CHECK (impact_score BETWEEN 1 AND 10),
    sentiment       TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
    telegram_sent   BOOLEAN DEFAULT FALSE,
    telegram_sent_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_created ON alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own alerts" ON alerts;
CREATE POLICY "Users can view own alerts"
    ON alerts FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all alerts" ON alerts;
CREATE POLICY "Service role can manage all alerts"
    ON alerts FOR ALL
    USING (auth.role() = 'service_role');


-- ── News Items ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS news_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN ('rss', 'api', 'social')),
    title           TEXT NOT NULL,
    url             TEXT,
    summary         TEXT,
    sentiment_score REAL,
    relevance_score REAL,
    raw_data        JSONB DEFAULT '{}',
    published_at    TIMESTAMPTZ,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (url)
);

CREATE INDEX IF NOT EXISTS idx_news_fetched ON news_items(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_items(source_type);

ALTER TABLE news_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view news" ON news_items;
CREATE POLICY "Authenticated users can view news"
    ON news_items FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Service role can manage all news" ON news_items;
CREATE POLICY "Service role can manage all news"
    ON news_items FOR ALL
    USING (auth.role() = 'service_role');


-- ── Agent Runs ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS agent_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES profiles(id) ON DELETE SET NULL,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    sources_checked INTEGER DEFAULT 0,
    items_found     INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    error_log       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_user ON agent_runs(user_id, started_at DESC);

ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own agent runs" ON agent_runs;
CREATE POLICY "Users can view own agent runs"
    ON agent_runs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all agent runs" ON agent_runs;
CREATE POLICY "Service role can manage all agent runs"
    ON agent_runs FOR ALL
    USING (auth.role() = 'service_role');


-- ── Auto-update updated_at trigger ──────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ── Auto-create profile on signup ───────────────────────────────────────────

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id)
    VALUES (NEW.id)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();
"""


if __name__ == "__main__":
    print(INIT_SQL)
    print("\\n-- Copy the SQL above and run it in Supabase Dashboard > SQL Editor")
