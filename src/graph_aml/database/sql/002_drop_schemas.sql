-- DESTRUCTIVE RESET SCRIPT.
-- WARNING: This script deletes all objects inside these schemas.
-- Use only when intentionally resetting local PostgreSQL state.

DROP SCHEMA IF EXISTS governance CASCADE;
DROP SCHEMA IF EXISTS aml CASCADE;
DROP SCHEMA IF EXISTS mart CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS raw CASCADE;
