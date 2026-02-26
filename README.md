# DE Portfolio Journal - Week 1
A Production grade ETL pipeline as a part of my 9-month data engineering study

## Current State
Read a CSV file, validates and cleans the data, then load the valid records.
Invalid records are skipped with warnings. All activity is logged through fileHandler and streamHandler.

# Current Project Structure
```
DE-PORTFOLIO
├── week1/
│   ├── __init__.py         # Package marker
│   ├── etl.py              # Main Extract, Transform, and Load functions
│   ├── logger.py           # Custom logging setup
│   ├── exceptions.py       # Current exception handlers (placeholder)
│   ├── config.py           # Environment variables loader
│   ├── requirements.txt    # Dependencies
├── .env                    # Local config - ignored for git
├── .env.example            # example for filling .env file
├── .gitignore
└── README.md 
```

## Environment Variables
| Variable | Required | Default | Description |
|---|---|---|---|
| DATA_FILEPATH | Yes | — | Path to input CSV file |
| LOG_LEVEL | No | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| PIPELINE_ENV | No | development | Environment name |


## Data Engineering Concepts Used
- Generator-based extraction - memory efficient data processing
- Custom exceptions - stage specific, for easier failure traceability
- Context Manager - safe file handling
- Structured logging - fileHandler and streamHandler logging with custom severity levels
- Environment variables - no hardcoded sensitive information, such as credentials
