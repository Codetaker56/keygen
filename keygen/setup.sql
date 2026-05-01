-- =============================================================
-- Supabase Setup: Key Management Table
-- Run this in your Supabase project's SQL Editor
-- =============================================================

-- Create the keys table
CREATE TABLE IF NOT EXISTS public.keys (
    id          BIGSERIAL PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index on key column for fast lookups during validation
CREATE INDEX IF NOT EXISTS idx_keys_key ON public.keys (key);

-- Disable Row Level Security so only the service role (server-side) can access
-- Your Flask API uses the service role key, so no RLS policies are needed.
-- IMPORTANT: Never expose the service role key to clients.
ALTER TABLE public.keys DISABLE ROW LEVEL SECURITY;

-- (Optional) If you prefer RLS enabled with explicit service-role bypass, do:
-- ALTER TABLE public.keys ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Service role only" ON public.keys
--     USING (auth.role() = 'service_role');
