-- ========================================
-- Nexus ERP - Database Initialization
-- ========================================
-- This script runs automatically on first startup
-- Creates necessary extensions and schemas
-- ========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema version table
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

-- Record initialization
INSERT INTO schema_version (version) VALUES ('init') ON CONFLICT DO NOTHING;

-- Set timezone
SET timezone = 'Asia/Riyadh';
