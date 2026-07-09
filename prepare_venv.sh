#!/bin/bash
python3 -mvenv .venv
. .venv/bin/activate

pip install -U pip
pip install -Ur requirements-run.txt
pip install -Ur requirements-parsers.txt
