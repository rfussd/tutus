.PHONY: install run test lint format typecheck clean

install:
	pip install -e .

run:
	tutus

test:
	python -m pytest -v --tb=short

test-coverage:
	python -m pytest --cov=core --cov=agents --cov=skills --cov=tests --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil; shutil.rmtree('.pytest_cache', ignore_errors=True)"
	python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"

precommit:
	pre-commit run --all-files
