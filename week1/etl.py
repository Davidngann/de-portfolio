import csv
from week1.logger import get_logger
from week1.exceptions import ExtractionError, TransformationError


logger = get_logger(__name__)


# Extraction Stage

def extract(filepath:str) -> list:
    logger.info(f"Starting extraction from {filepath}")

    try:
        records=[]
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        logger.info(f"Extracted {len(records)} records")
        return records

    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise ExtractionError(f"Cannot find file: {filepath}")

    except Exception as e:
        logger.error(f"unexpected error during extraction: {e}")
        raise ExtractionError(f"Extraction failed: {e}")
    

# Transformation Stage

def transform(data: list) -> list:
    logger.info(f"Starting transformaition on {len(data)} records")
    
    try:
        cleaned = []
        for row in data:

            # Skip rows with missing name
            if not row.get("name"):
                logger.warning(f"Skipping row with missing name: {row}")
                continue

            # Skip rows with invalid amount
            try:
                row['amount'] = float(row['amount'])
            except ValueError:
                logger.warning(f"Skipping row with invalid amount: {row}")
                continue

            cleaned.append(row)

        logger.info(f"Transformation completed. Transformed: {len(cleaned)} / {len(data)} records")
        return cleaned

    except Exception as e:
        logger.error(f"Unexpected error during transformation: {e}")
        raise TransformationError(f"Transformation failed: {e}")


# Load Stage

def load(data: list) -> None:
    logger.info(f"Loading {len(data)} records")
    for record in data:
        logger.debug(f"Record: {record}")

    logger.info("Load complete")

if __name__ == "__main__":
    data = extract("data.csv")
    data = transform(data)
    load(data)

    