.PHONY: run test clean docker-up docker-down docker-wipe logs parse-logs

run: 
	docker-compose run --rm etl python run.py

test:
	docker-compose run --rm etl pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} +

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