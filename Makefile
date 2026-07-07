.PHONY: test integration cli-smoke docs package binary docker-build web

test:
	python -m pytest

integration:
	python -m pytest tests/test_integration_runtime.py

cli-smoke:
	python -m pip install -e .[dev]
	aegiscode --help
	aegiscode doctor

web:
	aegiscode serve --host 0.0.0.0 --port 8080

docs:
	python scripts/build_docs.py

package:
	python -m build

binary:
	python scripts/build_binary.py

docker-build:
	docker build -t aegiscode:local .
