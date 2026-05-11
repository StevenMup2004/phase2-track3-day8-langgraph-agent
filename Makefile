.PHONY: install test lint typecheck run-scenarios run-scenarios-sqlite run-ui graph-diagram grade-local clean

install:
	pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check src tests

typecheck:
	mypy src

run-scenarios:
	python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json

run-scenarios-sqlite:
	python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.sqlite.yaml --output outputs/metrics.json

run-ui:
	streamlit run streamlit_app.py

graph-diagram:
	python -m langgraph_agent_lab.cli export-graph --output reports/graph.mmd

grade-local:
	python -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info outputs/*.json
