.PHONY: install build run run-staging test clean docker-up docker-down docker-wipe logs live-logs parse-logs ci ci-local

install:
	pip install -r requirements.txt

build:
	docker compose build etl

run: 
	docker compose run --rm etl python run.py

run-staging:
	docker compose run --rm etl python run.py --target-schema staging

test:
	docker compose run --rm etl pytest tests/ -v

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.pytest_cache')]"

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-wipe:
	docker compose down -v

logs:
	docker compose logs dbx

live-logs:
	docker compose logs -f etl dbx

parse-logs:
	python log_parser.py

ci:
	docker compose build etl
	docker compose up -d
	docker compose run --rm etl pytest tests/ -v
	docker compose down -v

ci-local:
	docker compose build etl
	docker compose up -d
	-docker compose run --rm etl pytest tests/ -v
	docker compose down -v