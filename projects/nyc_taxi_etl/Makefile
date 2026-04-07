.PHONY: install run run-staging test clean docker-up docker-down docker-wipe logs parse-logs

install:
	pip install -r requirements.txt

run: 
	docker-compose run --rm etl python run.py

run-staging:
	docker-compose run --rm etl python run.py --target-schema staging

test:
	docker-compose run --rm etl pytest tests/ -v

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.pytest_cache')]"

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-wipe:
	docker-compose down -v

logs:
	docker-compose logs -f etl

parse-logs:
	python log_parser.py