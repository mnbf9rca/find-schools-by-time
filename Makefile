CSV = $(lastword $(sort $(wildcard data/extract/edubasealldata*.csv)))

build:
	@trap 'rm -f schools.json.tmp' EXIT; uv run build_schools.py $(CSV) > schools.json.tmp && mv schools.json.tmp schools.json

run:
	op run --env-file=.env.tpl -- python3 app.py

.PHONY: build run
