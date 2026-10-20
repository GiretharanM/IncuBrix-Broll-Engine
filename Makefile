.PHONY: dev test lint compose-up compose-down clean

dev:
	docker compose up --build

test:
	pytest backend/tests -v

compose-up:
	docker compose up -d

compose-down:
	docker compose down

clean:
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
