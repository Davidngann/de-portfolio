# NYC Taxi ELT/ETL Pipeline

An end-to-end ELT/ETL pipeline processing NYC yellow taxi trip records through a three-layer PostgreSQL schema (raw → staging → reporting). Supports both Python-based transformation (ETL) and database-native transformation (ELT) via a CLI flag.

Built as part of a 9-month data engineering curriculum.

---

## Problem Statement
The NYC Taxi and Limousine commision publishes [monthly trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) in parquet format. Raw data contains invalid records, such as zero-fare trips, zero-distance trips, negative durations, and timestamp errors (potentially from DST boundary crossing). This pipeline extracts the raw file, enforces documented quality rules, and load only valid records into the structured PostgreSQL schema for downstream analysis.

---

## Architecture
Current PSQL Schema:
![Three-layer PSQL schema architecture](<img/three-layer schema architecture.png>)

| Layer | Table | Purpose |
|---|---|---|
| `raw` | `raw.yellow_trips` | Landing zone: all 20 source columns stored as TEXT, no cleaning |
| `staging` | `staging.yellow_trips` | Typed, constrained, cleaned, and business rules applied |
| `reporting` | `reporting.daily_metrics` | Aggregated daily metrics for downstream analysis |



### Two Pipeline Paths
 
The pipeline supports two execution paths selected via CLI flag.
 
**ELT Path (default) — transformation happens inside PostgreSQL**
 
```
yellow_tripdata_YYYY-MM.parquet
        │
        ▼
    extract()                ← schema validation against all 20 source columns
        │
        ▼
    load()                   ← batch insert to raw.yellow_trips (all TEXT)
        │
        ▼
    raw_to_staging.sql       ← column selection, type casting, null handling,
        │                      business rules, duration derivation (inside PSQL)
        ▼
    staging_to_reporting.sql ← daily aggregation with ON CONFLICT DO NOTHING
```
 
**ETL Path — transformation happens in Python**
 
```
yellow_tripdata_YYYY-MM.parquet
        │
        ▼
    extract()                ← schema validation against all 20 source columns
        │
        ▼
    transform()              ← column selection, null handling, business rules,
        │                      type casting, duration derivation (pandas)
        ▼
    validate_dataframe()     ← Great Expectations suite (6 expectations)
        │
        ▼
    load()                   ← batch insert to staging.yellow_trips
        │
        ▼
    staging_to_reporting.sql ← daily aggregation with ON CONFLICT DO NOTHING
```

---

## Tech stack
| Tool | Purpose |
|---|---|
| Python | Pipeline language |
| pandas | Extraction and transformation |
| psycopg2 | PostgreSQL connection and batch insert |
| pyarrow| Parquet file reading |
| python-dotenv | Environment variable management |
| Great Expectations | Data quality validation (ETL path) |
| pytest | Unit and integration test suite |
| PostgreSQL | Destination database |


---

## Project Structure
```
nyc_taxi_etl/
├── src/
│   ├── config.py           # Environment variable loader with validation
│   ├── exceptions.py       # Custom exceptions per pipeline stage
│   ├── extract.py          # Parquet reading and schema validation
│   ├── transform.py        # Cleaning, casting, and derivation (ETL path)
│   ├── load.py             # Batch insert, SQL execution, connection management
│   ├── validate.py         # Great Expectations suite
│   └── logger.py           # Dual-handler logger (console + file)
├── sql/
│   ├── create_table.sql            # Three-layer schema DDL
│   ├── raw_to_staging.sql          # ELT transformation inside PostgreSQL
│   └── staging_to_reporting.sql    # Daily aggregation with upsert guard
├── tests/
│   ├── conftest.py         # Shared fixtures and test DB config
│   ├── test_extract.py     # Extract stage tests
│   ├── test_transform.py   # Transform stage tests
│   └── test_load.py        # Load stage integration tests
├── data/                   # Source files - gitignored
├── logs/                   # Pipeline logs - gitignored
├── .env.example            # Required environment variables
├── requirements.txt        # Dependencies
└── run.py                  # Entry point with argparse
```

---

## Setup
### OPTION 1 - Docker (RECOMMENDED)
Requires Docker Desktop installed and running.

### 1. Clone the repo and navigate to project folder
**If you want to run without cloning the repo**, pull the pre-built image:
```bash
docker pull davidngan/nyc-taxi-etl
```
Then in `docker-compose.yml`, swap:
```yaml
# Comment this out:
# build: .

# Uncomment this:
image: davidngan/nyc-taxi-etl:latest
```

**If you want to build from source**, clone and run normally:
```bash
git clone https://github.com/Davidngann/de-portfolio.git
cd de-portfolio/projects/nyc_taxi_etl
make docker-up
```

### 2. Copy `.env.example` to `.env` and fill in your credentials
```bash
cp .env.example .env
# Edit .env with your preferred PostgreSQL credentials and source filename
```

### 3. Place your source parquet file in `data/`
Download Yellow Taxi trip records (Parquet format) from the [TLC Trip Record Data page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) and place the file in the `data/` folder.

### 4. Run the pipeline:

```bash
make run
```

The stack starts PostgreSQL, creates the schema automatically,
and runs the ETL pipeline. Logs are written to `logs/pipeline.log`.

To run the ETL path instead of the default ELT path:
```bash
make run-staging
```

[Docker Hub image](https://hub.docker.com/r/davidngan/nyc-taxi-etl)

---
### OPTION 2 - Local Setup (MANUAL)
### 1. Clone the repo
 
```bash
git clone https://github.com/Davidngann/de-portfolio.git
cd de-portfolio/projects/nyc_taxi_etl
```
 
### 2. Create virtual environment
 
```bash
python -m venv .venv
.\.venv\Scripts\activate     # Windows
source .venv/bin/activate    # Mac/Linux
```
 
### 3. Install dependencies
 
```bash
make install
```
 
### 4. Configure environment
 
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and source filename
```
 
### 5. Download source data
 
Download Yellow Taxi trip records (Parquet format) from the [TLC Trip Record Data page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) and place the file in the `data/` folder.
 
### 6. Create the destination schemas
 
Create two databases — `taxi_db` (production) and `taxi_db_test` (tests) — then run:
 
```bash
psql -U {username} -d taxi_db -f sql/create_table.sql
psql -U {username} -d taxi_db_test -f sql/create_table.sql
```
 
### 7. Run the pipeline
 
```bash
# ELT path (default) — loads raw data to PostgreSQL, transforms via SQL
python run.py --target-schema raw
 
# ETL path — transforms via Python, loads directly to staging
python run.py --target-schema staging
```

---

## Available Make Commands
| Command | Description |
|---|---|
| `make docker-up` | Build image and start all services |
| `make docker-down` | Stop containers, keep volume |
| `make docker-wipe` | Stop containers and delete volume |
| `make run` | Run the ELT pipeline (loads to raw) |
| `make run-staging` | Run the ETL pipeline (transforms in Python, loads to staging) |
| `make test` | Run the full test suite |
| `make clean` | Remove Python cache files |
| `make logs` | Tail ETL container logs |
| `make parse-logs` | Print log summary with error count |

---

## Data quality rules
### Column selection (10 of 20 used in staging)
 
| Column | Kept | Reason |
|---|---|---|
| `tpep_pickup_datetime` | ✓ | Required for duration derivation |
| `tpep_dropoff_datetime` | ✓ | Required for duration derivation |
| `passenger_count` | ✓ | Operational metric |
| `trip_distance` | ✓ | Core business metric |
| `PULocationID` | ✓ | Required for zone analysis |
| `DOLocationID` | ✓ | Required for zone analysis |
| `fare_amount` | ✓ | Core financial metric |
| `tip_amount` | ✓ | Financial metric |
| `total_amount` | ✓ | Core financial metric |
| `payment_type` | ✓ | Operational metric |
The remaining 10 columns are preserved in `raw.yellow_trips` for auditability.


### Null handling
| Column | Rule | Reason |
|---|---|---|
| `pickup_at`, `dropoff_at` | DROP | Duration cannot be derived without both |
| `trip_distance` | DROP | Core business metric |
| `fare_amount` | DROP | Core business metric |
| `total_amount` | DROP | Core business metric |
| `pickup_zone_id` | DROP | NOT NULL in destination schema |
| `dropoff_zone_id` | DROP | NOT NULL in destination schema |
| `passenger_count` | KEEP | Self-reported, often missing, still usable |
| `tip_amount` | KEEP | Missing tip treated as $0 |
| `payment_type` | KEEP | Row is usable without payment method |



### Business rules filter
| Rule | Reason |
|---|---|
| `trip_distance > 0` | Zero-distance trips are not real trips |
| `fare_amount > 0` | Zero-fare trips are not valid records |
| `total_amount > 0` | Zero total amount trips are not valid records |
| `trip_duration_minutes > 0` | Negative duration indicates a timestamp error |
| `trip_duration_minutes ≤ 1440` | Trips over 24 hours treated as corrupt data |

---
## Sample Results
 
Dataset: `yellow_tripdata_2025-04.parquet`
 
**ELT Path**
 
| Stage | Rows |
|---|---|
| Extracted → `raw.yellow_trips` | 3,970,553 |
| `raw_to_staging.sql` → `staging.yellow_trips` | 3,672,139 |
| `staging_to_reporting.sql` → `reporting.daily_metrics` | 32 |
 
Load time: ~15 min 58 sec · Batch size: 5,000 · Total batches: 795

<details>
<summary> ELT log result snippet </summary>

```
2026-03-28 17:03:38,295 | INFO | __main__ | Pipeline starting | ENV: DEVELOPMENT | Target Schema: raw
2026-03-28 17:03:38,296 | INFO | src.extract | Starting extraction from <location>\de-portfolio\projects\nyc_taxi_etl\data\yellow_tripdata_2025-04.parquet
2026-03-28 17:03:40,908 | INFO | src.extract | Raw file loaded: 3,970,553, rows, 20 columns
2026-03-28 17:03:40,911 | INFO | src.extract | Schema validation passed
2026-03-28 17:03:40,911 | INFO | src.extract | Extraction complete: 3,970,553 rows returned
2026-03-28 17:06:03,132 | INFO | src.load | [raw] starting load: 3,970,553 rows | Batch size: 5,000 | Total batches: 795
2026-03-28 17:06:04,595 | INFO | src.load | Batch for raw: 1/795 | Rows loaded: 5,000/3,970,553
2026-03-28 17:06:05,517 | INFO | src.load | Batch for raw: 2/795 | Rows loaded: 10,000/3,970,553
...
...
2026-03-28 17:18:57,730 | INFO | src.load | Load complete | 3,970,553 rows inserted across 795 batches
2026-03-28 17:18:57,731 | INFO | src.load | Database connection closed
2026-03-28 17:19:00,529 | INFO | src.load | Starting SQL script: sql/raw_to_staging.sql
2026-03-28 17:21:51,186 | INFO | src.load | SQL script executed: sql/raw_to_staging.sql | PSQL Status: INSERT 0 3672139 | Rows affected: 3,672,139
2026-03-28 17:21:51,186 | INFO | src.load | Successfully executed sql script: sql/raw_to_staging.sql
2026-03-28 17:21:51,190 | INFO | src.load | Database connection closed
2026-03-28 17:21:51,305 | INFO | src.load | Starting SQL script: sql/staging_to_reporting.sql
2026-03-28 17:22:01,291 | INFO | src.load | SQL script executed: sql/staging_to_reporting.sql | PSQL Status: INSERT 0 32 | Rows affected: 32
2026-03-28 17:22:01,292 | INFO | src.load | Successfully executed sql script: sql/staging_to_reporting.sql
2026-03-28 17:22:01,294 | INFO | src.load | Database connection closed
2026-03-28 17:22:01,295 | INFO | __main__ | Pipeline complete

```

</details>

---

**ETL Path**
 
| Stage | Rows |
|---|---|
| Extracted | 3,970,553 |
| After null handling | 3,970,553 |
| After business rule filters | 3,706,063 |
| After duration filters | 3,672,139 |
| Loaded → `staging.yellow_trips` | 3,672,139 |
| Aggregated → `reporting.daily_metrics` | 32 |
| Total dropped | 298,414 (7.5%) |
 
Load time: ~7 min 46 sec · Batch size: 5,000 · Total batches: 735

<details>
<summary> ETL log result snippet </summary>

```
2026-03-28 17:26:00,233 | INFO | __main__ | Pipeline starting | ENV: DEVELOPMENT | Target Schema: staging
2026-03-28 17:26:00,233 | INFO | src.extract | Starting extraction from <location>\de-portfolio\projects\nyc_taxi_etl\data\yellow_tripdata_2025-04.parquet
2026-03-28 17:26:01,023 | INFO | src.extract | Raw file loaded: 3,970,553, rows, 20 columns
2026-03-28 17:26:01,024 | INFO | src.extract | Schema validation passed
2026-03-28 17:26:01,025 | INFO | src.extract | Extraction complete: 3,970,553 rows returned
2026-03-28 17:26:01,025 | INFO | src.transform | Starting transformation: 3,970,553, rows received
2026-03-28 17:26:01,027 | INFO | src.transform | Schema validation for transformation passed
2026-03-28 17:26:01,429 | INFO | src.transform | Null drop complete: 0 rows removed, 3,970,553 remaining | dropped percentage: 0.0%
2026-03-28 17:26:02,524 | INFO | src.transform | Business rule filter complete: 264,490 rows removed, 3,706,063 remaining | dropped percentage: 6.7% 
2026-03-28 17:26:02,693 | INFO | src.transform | Type casting complete
2026-03-28 17:26:03,301 | INFO | src.transform | Duration filter complete: 33,924 rows removed, 3,672,139 remaining | dropped percentage: 0.9% 
2026-03-28 17:26:03,304 | INFO | src.transform | Transformation complete: 3,672,139 rows ready for load | total dropped: 298,414  | % dropped from initial: 7.5%
2026-03-28 17:26:05,563 | INFO | src.validate | GE validation passed at transform stage | 6 expectations checked
2026-03-28 17:27:29,761 | INFO | src.load | [staging] starting load: 3,672,139 rows | Batch size: 5,000 | Total batches: 735
2026-03-28 17:27:30,247 | INFO | src.load | Batch for staging: 1/735 | Rows loaded: 5,000/3,672,139
2026-03-28 17:27:30,679 | INFO | src.load | Batch for staging: 2/735 | Rows loaded: 10,000/3,672,139
...
...
2026-03-28 17:33:46,518 | INFO | src.load | Batch for staging: 735/735 | Rows loaded: 3,672,139/3,672,139
2026-03-28 17:33:46,518 | INFO | src.load | Load complete | 3,672,139 rows inserted across 735 batches
2026-03-28 17:33:46,519 | INFO | src.load | Database connection closed
2026-03-28 17:33:48,059 | INFO | src.load | Starting SQL script: sql/staging_to_reporting.sql
2026-03-28 17:33:53,056 | INFO | src.load | SQL script executed: sql/staging_to_reporting.sql | PSQL Status: INSERT 0 32 | Rows affected: 32
2026-03-28 17:33:53,056 | INFO | src.load | Successfully executed sql script: sql/staging_to_reporting.sql
2026-03-28 17:33:53,059 | INFO | src.load | Database connection closed
2026-03-28 17:33:53,059 | INFO | __main__ | Pipeline complete
```

</details>

---

## Testing
### Test Suite overview
| File | Tests | What it covers |
|---|---|---|
| `test_extract.py` | 5 | Schema validation, missing file, unreadable file, missing columns, empty file |
| `test_transform.py` | 14 | Column selection, business rules, null handling, type casting, column rename, duration filters, row counts |
| `test_load.py` | 7 | Row counts to raw and staging, bad connection config, batch size variations, invalid schema |

### Running tests
 
```bash
# Full suite
pytest
 
# Verbose output
pytest -v
 
# Single file
pytest tests/test_transform.py -v
 
# With coverage report
pytest --cov=src --cov-report=term-missing
```

### Coverage
 
| File | Coverage | Notes |
|---|---|---|
| `extract.py` | 100% | — |
| `transform.py` | 97% | Generic `except Exception` handler not reachable in tests |
| `load.py` | 74% | Batch failure path and SQL error paths not tested |
| `validate.py` | 0% | GE runs via `run.py`, not called in test suite |
| `config.py` | 0% | Verified via pipeline run |
 
**Overall: 72%**


### Great Expectations
6 expectations run automatically after `transform()` before `load()`:
 
| Column | Expectation |
|---|---|
| `fare_amount` | Not null, must be > 0 |
| `trip_distance` | Not null, must be > 0 |
| `pickup_zone_id` | Not null |
| `trip_duration_minutes` | Must be > 0 and ≤ 1440 |
 
Pipeline raises `TransformationError` and halts if any expectation fails.

### Known coverage gaps
 
- `validate.py` — no pytest coverage. Verified manually by injecting a bad row and confirming `TransformationError` is raised.
- `load.py` — SQL script execution error paths verified manually in PgAdmin.
- `load.py` — per-batch failure path not tested.
- Great Expectations applies to ETL path only.


## Known Limitations
**No raw layer idempotency** — Re-running the pipeline on the same source file appends duplicate rows to `raw.yellow_trips`. There is no deduplication at the raw layer. Staging row counts will exceed raw counts on repeated runs.
 
**Two transformation paths require manual sync** — Business rule changes must be applied to both `transform.py` and `raw_to_staging.sql` independently. No automated test verifies parity between the two paths.
 
**Full file load only** — The pipeline loads the entire source file on every run. Incremental loading is not implemented.
 
**Single file only** — The pipeline processes one file specified in `SOURCE_FILE`. Multiple files are not detected or processed automatically.

**Source data contains boundary dates from adjacent months**: The TLC parquet files for a given month include trips whose pickup timestamps fall outside that month. For example, `yellow_tripdata_2025-04.parquet` contains trips recorded on 2025-03-31 and 2025-05-01. As a result, `reporting.daily_metrics` will contain rows for dates outside the nominal month range. 
If `yellow_tripdata_2025-03.parquet` and `yellow_tripdata_2025-04.parquet` are both loaded into the same database, both files will contribute trips for 2025-03-31. The ON CONFLICT DO NOTHING guard on reporting.daily_metrics means whichever month runs first wins. The second run's data for that boundary date is silently discarded. The same applies to the last day of each month. 

---

## RUNBOOK
**Pipeline exits with `ExtractionError`**
Cause: Source file missing or column schema mismatch
Debug: Run `cat logs/pipeline.log` or `make parse-logs`
Fix: Verify `data/` contains the correct parquet file and `SOURCE_FILE` in `.env` match the filename exactly
Then re-run with `make run` (ELT) or `make run-staging` (ETL)

**Pipeline exits with `LoadError: relation does not exist`**
Cause: Database schema not initialized, volume was created before init SQL ran.
Debug: `docker-compose logs dbx` -> check for schema creation errors
Fix: `make docker-wipe` -> `make docker-up` to force schema initialization

**`make test` fails with `database taxi_db_test does not exist`**
Cause: Test database not created, Volume is stale
Debug: Check whether `02_create_test_db.sql` is in `docker-compose.yml` or not
Fix: `make docker-wipe` -> `make docker-up` -> `make-test`




---
## Environment Variables
| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_HOST` | Yes | — | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | Yes | — | Production database name |
| `TEST_DB_NAME` | Yes | — | Test database name |
| `DB_USER` | Yes | — | Database user |
| `DB_PASSWORD` | Yes | — | Database password |
| `SOURCE_FILE` | Yes | — | Parquet filename in `data/` |
| `BATCH_SIZE` | No | `5000` | Rows per insert batch |
