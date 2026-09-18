#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODEL_SQL_DIR="$ROOT/sql_v3_2/modeling"
AUDIT_SQL_DIR="$ROOT/sql_v3_2/audits"
RUN_DIR="$ROOT/project_control/runs/20260828_v3_3_compact_features"
PSQL=${PSQL:-/Library/PostgreSQL/12/bin/psql}
PGHOST=${PGHOST:-localhost}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-mimiciv31}

mkdir -p "$RUN_DIR/logs" "$RUN_DIR/reports" "$RUN_DIR/data"

for file in \
    090A_create_modeling_base_v33.sql \
    090B_create_compact_predictors_v33.sql \
    090C_create_modeling_input_v33.sql
do
    echo "Running $file"
    "$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
        -f "$MODEL_SQL_DIR/$file" > "$RUN_DIR/logs/$file.log" 2>&1 || {
        echo "FAILED: $file"
        tail -40 "$RUN_DIR/logs/$file.log"
        exit 1
    }
done

echo "Running 090D_export_compact_feature_qc_v33.sql"
"$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$AUDIT_SQL_DIR/090D_export_compact_feature_qc_v33.sql" \
    > "$RUN_DIR/logs/090D_export_compact_feature_qc_v33.sql.log" 2>&1 || {
    echo "FAILED: 090D_export_compact_feature_qc_v33.sql"
    tail -40 "$RUN_DIR/logs/090D_export_compact_feature_qc_v33.sql.log"
    exit 1
}

echo "[OK] v3.3 compact feature rebuild completed. Outputs in $RUN_DIR"

