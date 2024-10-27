bench: venv
	TEMP=/run/user/$(shell id -u) ./.venv/bin/python3 run.py

plot:
	./.venv/bin/python3 render_plots.py

markdown:
	./.venv/bin/python3 render_markdown.py

venv:
	bash prepare_venv.sh

