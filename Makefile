.PHONY: test demo web docker-build

test:
	python -m pytest

demo:
	python scripts/mechanism_demo.py --case all

web:
	python -m aegis_harness.web --host 0.0.0.0 --port 8080

docker-build:
	docker build -t aegis-code-harness:local .
