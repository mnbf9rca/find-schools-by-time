CSV = $(lastword $(sort $(wildcard data/extract/edubasealldata*.csv)))

RESULTS_CSV = $(lastword $(sort $(wildcard data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_*_API.csv)))

build:
	@trap 'rm -f schools.json.tmp' EXIT; uv run build_schools.py $(CSV) $(RESULTS_CSV) > schools.json.tmp && mv schools.json.tmp schools.json

run:
	op run --env-file=.env.tpl -- python3 app.py

origins:
	uv run --with pyproj fixtures/make_origins.py

.PHONY: build run origins
