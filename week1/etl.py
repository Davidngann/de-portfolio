from week1.logger import get_logger

logger = get_logger(__name__)

def extract(filepath:str) -> list:
    logger.info(f"Extracting data from {filepath}")
    return []

def transform(data: list) -> list:
    logger.debug(f"Transforming {len(data)} records")
    return data

def load(data: list) -> None:
    logger.info(f"Loading {len(data)} records")

if __name__ == "__main__":
    data = extract("data.csv")
    data = transform(data)
    load(data)

    