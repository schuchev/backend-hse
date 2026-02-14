.PHONY: up down api worker test

up:
	docker compose up -d

down:
	docker compose down

api:
	python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

worker:
	python -m app.workers.moderation_worker

test:
	python -m pytest -vv
