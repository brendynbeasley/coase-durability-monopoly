# Rebuild everything from the public source files.
#   make all      download data, build the panel, run theory and empirics, test
#   make data     download Census and BEA files and build data/processed/
#   make results  run the theory simulations and the empirical test
#   make test     run the test suite

PY ?= python

.PHONY: all data results theory empirics test clean

all: data results test

data:
	"$(PY)" scripts/build_data.py

results: theory empirics

theory:
	"$(PY)" scripts/run_experiments.py

empirics:
	"$(PY)" scripts/run_empirics.py

test:
	"$(PY)" -m pytest -q

clean:
	rm -rf data/raw results/empirics
