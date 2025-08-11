# 0002 — Database backend
- **Status:** Accepted
- **Date:** 2025-08-11

## Context
Primary system of record is a relational DB (SQL Server expected in production).

## Decision
Use a proven Django SQL Server backend (`mssql-django`) for production; pin versions in CI.

## Consequences
- Configure `DATABASES` accordingly.
- Include integration tests around stored procedure calls.
