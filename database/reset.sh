#!/usr/bin/env bash
# Wipe data but keep schema, then reseed.  Usage: ./db/reset.sh  (run from repo root)
set -e
cd backend && python -m db.seed.seed_demo 2>/dev/null || python ../db/seed/seed_demo.py
