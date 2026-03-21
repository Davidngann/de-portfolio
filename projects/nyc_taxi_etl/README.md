# NYC taxi ETL Pipeline

An ETL pipeline that extract NYC yellow taxi trips records, applies documented data quality rules, and load clean records to the PostgreSQL.

Built as my week 3 deliverables of a 9-month data engineering study.

---

## Problem Statement
The NYC Taxi and Limousine commision publishes [monthly trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) in parquet format. Raw data contains invalid records, such as zero-fare trips, zero-distance trips, negative durations, and timestamp errors (potentially from DST boundary crossing). This pipeline extracts the raw file, enforces documented quality rules, and load only valid records into the structured PostgreSQL schema for downstream analysis.

---

## Architecture
```
yellow_tripdata_YYYY-MM.parquet
        │
        ▼
    extract()
    - Schema validation
    - Column selection (selected 10 columns for downstream analysis)
        │
        ▼
    transform()
    - Null handling
    - Business rules filters
    - Type casting
    - trip_duration_minutes derivation
    - Column rename to match destination schema
        │
        ▼
    load()
    - Batch insert with psycopg2.extras.execute_values()
    - 5,000 rows per batch
    - Per-batch transaction handling (rollback/commit)
        │
        ▼
staging.yellow_trips (PostgreSQL)
```

---

## Tech stack
| Tool | Purpose |
|---|---|
|Python 3.12 | Pipeline language|
| pandas | Extraction and transformation |
| psycopg2 | PostgreSQL connection and batch insert |
| python-dotenv | Environment variables management | 
| pyarrow | Parquet file reading | 
| PostgreSQL 17 | Destination database

---

## Project Structure
```
nyc_taxi_etl/
├── src/
|   ├── config.py       # Environment variables loader
|   ├── exceptions.py   # Custom exceptions per pipeline stage
|   ├── extract.py      # Extraction and schema validation
|   ├── transform.py    # Cleaning, casting, and derivation
|   ├── load.py         # Batch insert into PostgreSQL
|   ├── logger.py       # Dual handler logger (console + log file)
├── sql/
|   ├── create_table.sql    # Create destination schema and table
├── data/                 # Source file folder - gitignored
├── logs/                 # Pipeline logs - gitignored
├── .env.example          # Required environment variables
├── requirements.txt      # List of required libraries
├── run.py                # Entry point
└── README.MD
```

---

## Setup
### 1. Clone the repo
```bash
git clone https://github.com/Davidngann/de-portfolio.git
cd de-portfolio/projects/nyc_taxi_etl
```
### 2. Create virtual environment
```bash
python -m venv .venv
.\.venv\Scripts\activate        # for windows
source .venv/bin/activate       # for Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and source file name
```

### 5. Download the source data
Download Yellow Taxi trip records (Parquet format) from:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Place the file in the `data/` folder.

### 6. Create the destination schema
```bash
psql -U user_name -d taxi_db -f sql/create_table.sql
```

### 7. Run the pipeline
```bash
python run.py
```
---

## Data quality rules
### Columns selected (10 of 20)
- `tpep_pickup_datetime`
- `tpep_dropoff_datetime`
- `passenger_count`
- `trip_distance`
- `PULocationID`
- `DOLocationID`
- `fare_amount` 
- `tip_amount`
- `total_amount`
- `payment_type`

### Null handling
| Column | Rule | Reason |
|---|---|---|
| pickup_at, dropoff_at | DROP | Duration cannot be derived without both |
| trip_distance | DROP | Core business metric |
| fare_amount | DROP | Core business metric |
| total_amount | DROP | Core business metric |
| pickup_zone_id | DROP | Not nullable in destination schema |
| dropoff_zone_id | DROP | Not nullable in destination schema |
| passenger_count | KEEP | Self-reported, often missing, but still usable |
| tip_amount | KEEP | Missing tip means $0 tip in many cases |
| payment_type | KEEP | Useful row overall without payment method |


### Business rules filter
| Rule | Reason |
|---|---|
| trip_distance > 0 | Zero-distance trips are not real trips |
| fare_amount > 0 | Zero-fare trips are not valid records |
| trip_duration_minutes > 0 | Negative duration = timestamp error |
| trip_duration_minutes ≤ 1440 | Trips over 24 hours treated as corrupt data |

---
## Sample result
The dataset used is: `yellow_tripdata_2025-04.parquet`
| Stage | Remaining rows |
|---|---|
| Raw (extracted) | 3,970,553 |
| Null handling | 3,970,553 | 
| After business rule filters | 3,706,107 |
| After duration < 0 filter | 3,672,189 |
| After duration >= 1440 filter | 3,672,168 |
| Loaded to PostgreSQL | 3,672,168 |
| Total dropped | 298,385 (7.5%) |

Load time: ~6 minutes 26 seconds
Batch size: 5,000 rows
Total batches: 735

<details>
<summary> Logging in console view example </summary>

```
2026-03-13 21:49:44,256 | INFO | __main__ | Pipeline starting | ENV: DEVELOPMENT
2026-03-13 21:49:44,257 | INFO | src.extract | Starting extraction from <location>\projects\nyc_taxi_etl\data\yellow_tripdata_2025-04.parquet
2026-03-13 21:49:46,574 | INFO | src.extract | Raw file loaded: 3,970,553, rows, 20 columns
2026-03-13 21:49:46,579 | INFO | src.extract | Schema validation passed
2026-03-13 21:49:46,790 | INFO | src.extract | Extraction complete: 3,970,553 rows returned
2026-03-13 21:49:46,791 | INFO | src.transform | Starting transformation: 3,970,553, rows received
2026-03-13 21:49:46,964 | INFO | src.transform | Null drop complete: 0 rows removed, 3,970,553 remaining | dropped percentage: 0.0%
2026-03-13 21:49:47,827 | INFO | src.transform | Business rule filter complete: 264,446 rows removed, 3,706,107 remaining | dropped percentage: 7.1%
2026-03-13 21:49:48,022 | INFO | src.transform | Type casting complete
2026-03-13 21:49:48,704 | INFO | src.transform | Duration filter complete: 33,918 rows removed, 3,672,189 remaining | dropped percentage: 0.9%
2026-03-13 21:49:49,184 | INFO | src.transform | Max duration filter complete: 21 rows removed, 3,672,168 remaining | dropped percentage: 0.0%
2026-03-13 21:49:49,186 | INFO | src.transform | Transformation complete: 3,672,168 rows ready for load | total dropped: 298,385  | % dropped from initial: 7.5%
2026-03-13 21:49:49,187 | INFO | src.load | Starting load with: 3,672,168 rows | Batch size: 5,000 | Total batches: 735
2026-03-13 21:50:49,434 | INFO | src.load |  Batch 1/735 | Rows loaded: 5,000/3,672,168
2026-03-13 21:50:49,924 | INFO | src.load |  Batch 2/735 | Rows loaded: 10,000/3,672,168
2026-03-13 21:50:50,363 | INFO | src.load |  Batch 3/735 | Rows loaded: 15,000/3,672,168
...
...
2026-03-13 21:56:59,650 | INFO | src.load |  Batch 734/735 | Rows loaded: 3,670,000/3,672,168
2026-03-13 21:56:59,877 | INFO | src.load |  Batch 735/735 | Rows loaded: 3,672,168/3,672,168
2026-03-13 21:56:59,878 | INFO | src.load | Database connection closed
2026-03-13 21:56:59,878 | INFO | src.load | Load complete | 3,672,168 rows inserted across 735 batches
2026-03-13 21:57:01,391 | INFO | __main__ | Pipeline complete
```

</details>

---

## Known Limitations
**Full file load only** -> The pipeline loads the entire source file on every run rather than loading incrementally.

**No automated tests** -> Will be added within the next 1-2 weeks.

**No Idempotency** -> Re-running the pipeline inserts duplicate rows because `trip_id` is a `BIGSERIAL` with no natural key constraint.
Fix planned in the next few weeks with airflow and `ON CONFLICT DO NOTHING`.

**Single file only:** The pipeline processes one file specified in `SOURCE_FILE`.
Multiple files in `data/` are not detected or processed automatically.
Fix planned in the next few weeks with airflow.

---
| Variable | Required | Default | Description |
|---|---|---|---|
| DB_HOST | Yes | — | PostgreSQL host |
| DB_PORT | No | 5432 | PostgreSQL port |
| DB_NAME | Yes | — | Database name |
| DB_USER | Yes | — | Database user |
| DB_PASSWORD | Yes | — | Database password |
| SOURCE_FILE | Yes | — | Parquet filename in data/ |
| BATCH_SIZE | No | 5000 | Rows per insert batch |


---
---
## Testing
### Test Suite overview
| File | Tests | What it covers |
|---|---|---|
| `tests/test_extract.py` | 4 | Schema validation, missing file, missing expected columns, empty file |
| `tests/test_transform.py` | 12 | Business rule, null handling, type casting, column rename, row counts, duration rules |
| `tests/test_load.py` | 5 | Row counts, bad connection config, batch size variations (parametrized) |

### How to run the test
**Run the full suite from the project root:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run a single test file:**
```bash
pytest projects/nyc_taxi_etl/tests/test_transform.py -v
```

**Run with coverage report:**
```bash
pytest --cov=src --cov-report=term-missing
```

### Coverage
| File | Coverage | Notes |
|---|---|---|
| `extract.py` | 100% | - |
| `transform.py` | 96% | Generic unexpected exception handler not covered | 
| `load.py` | 92% | Per-batch failure path not tested |
| `validate.py` | 0% | GE runs via `run.py`, not called in test suite |
| `config.py` | 0% | Verified via pipeline run, not unit tests |

Overall Coverage: 77%

### Great Expectations
6 data quality expectations run automatically after `transform()` and before `load()` as part of `python run.py`:
- `fare_amount` -> No nulls, must be above 0
- `trip_distance` -> No nulls, must be above 0
- `pickup_zone_id` -> No nulls
- `trip_duration_minutes` -> Must be `>0` and `<=1440` minutes 

Pipeline raises `TransformationError` nd stops if any expectation fails.

# Known coverage gaps
- `validate.py` -> no pytest coverage. Still verified manually by injecting a bad row and confirming `TransformationError` is raised correctly
- Batch failure path in `load.py` is not tested yet.