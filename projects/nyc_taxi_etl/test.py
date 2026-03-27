from src.extract import extract
from src.config import get_config


def main():
    config=get_config()

    df_raw = extract(config['source_file'])
    print(df_raw.head())

if __name__ == "__main__":
    main()