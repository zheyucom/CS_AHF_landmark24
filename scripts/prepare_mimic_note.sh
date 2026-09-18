#!/bin/sh
set -eu

# Prepare/load the official MIMIC-IV-Note PostgreSQL schema.
# The data directory must already be downloaded by the authorized user.
# Existing mimiciv_note is never replaced unless ALLOW_REPLACE_NOTE_SCHEMA=1.

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
NOTE_CODE=${NOTE_CODE:-/Users/zheyu/Desktop/Task/26.4 CS_403/mimic-code/mimic-iv-note}
PSQL=${PSQL:-/Library/PostgreSQL/12/bin/psql}
PGHOST=${PGHOST:-localhost}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-mimiciv31}
NOTE_DATA_DIR=${1:-}

if [ ! -x "$PSQL" ]; then
    echo "psql not found or not executable: $PSQL" >&2
    echo "Set PSQL=/path/to/psql and retry." >&2
    exit 1
fi

if [ -z "$NOTE_DATA_DIR" ]; then
    echo "Usage: $0 /path/to/mimic-iv-note/2.2/note" >&2
    exit 2
fi

for file in discharge.csv.gz radiology.csv.gz discharge_detail.csv.gz radiology_detail.csv.gz; do
    if [ ! -f "$NOTE_DATA_DIR/$file" ]; then
        echo "Missing $NOTE_DATA_DIR/$file" >&2
        exit 1
    fi
done

if [ ! -r "$NOTE_DATA_DIR/discharge.csv.gz" ] || \
   [ ! -r "$NOTE_DATA_DIR/radiology.csv.gz" ] || \
   [ ! -r "$NOTE_DATA_DIR/discharge_detail.csv.gz" ] || \
   [ ! -r "$NOTE_DATA_DIR/radiology_detail.csv.gz" ]; then
    echo "All Note files must be readable by the current user." >&2
    exit 1
fi

echo "Checking PostgreSQL connection: $PGUSER@$PGHOST/$PGDATABASE"
if ! "$PSQL" -X -w -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -Atc \
    "select current_database(), current_user" >/dev/null; then
    echo "PostgreSQL connection failed without prompting for a password." >&2
    echo "Configure ~/.pgpass or export PGPASSWORD for this process, then retry." >&2
    exit 1
fi

if [ "${NOTE_SKIP_SPACE_CHECK:-0}" != "1" ]; then
    available_kb=$(df -Pk "$NOTE_DATA_DIR" | awk 'NR==2 {print $4}')
    required_kb=${NOTE_REQUIRED_KB:-15000000}
    if [ -n "$available_kb" ] && [ "$available_kb" -lt "$required_kb" ]; then
        echo "Insufficient free disk space: ${available_kb} KB available, ${required_kb} KB required." >&2
        echo "Set NOTE_SKIP_SPACE_CHECK=1 only after confirming storage manually." >&2
        exit 1
    fi
fi

if [ "${ALLOW_REPLACE_NOTE_SCHEMA:-0}" != "1" ]; then
    exists=$($PSQL -X -w -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -Atc \
        "select case when exists (select 1 from pg_namespace where nspname='mimiciv_note') then 1 else 0 end")
    if [ "$exists" = "1" ]; then
        echo "mimiciv_note already exists; set ALLOW_REPLACE_NOTE_SCHEMA=1 only after backup/review." >&2
        exit 1
    fi
fi

"$PSQL" -X -w -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$NOTE_CODE/buildmimic/postgres/create.sql"
"$PSQL" -X -w -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -v "mimic_data_dir=$NOTE_DATA_DIR" \
    -f "$NOTE_CODE/buildmimic/postgres/load_gz.sql"
"$PSQL" -X -w -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$NOTE_CODE/buildmimic/postgres/validate.sql"

"$PSQL" -X -w -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$ROOT/sql_v3_2/audits/100_audit_note_source_availability.sql"

echo "[OK] MIMIC-IV-Note loaded and audited."
