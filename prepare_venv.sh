#!/bin/bash
python3 -mvenv .venv
. .venv/bin/activate

pip install -U pip
pip install -r requirements-run.txt
pip install -r requirements-parsers.txt
