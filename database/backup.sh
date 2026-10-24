#!/usr/bin/env bash
# Backup:  ./db/backup.sh        Restore: cat backup.sql | docker exec -i stocksense-db psql -U stocksense stocksense
docker exec stocksense-db pg_dump -U stocksense stocksense > "backup_$(date +%F_%H%M).sql"
