bench: venv
	TEMP=/run/user/$(shell id -u) ./venv/bin/python3 run_all.py

venv:
	bash prepare_venv.sh

