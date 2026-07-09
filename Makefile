bench:
	sync
	echo 3 > /proc/sys/vm/drop_caches
	TEMP=/run/user/$(shell id -u) taskset -c 0 nice -n -20 chrt -f 99 ./.venv/bin/python3 run.py --append

plot:
	./.venv/bin/python3 render_plots.py

readme:
	./.venv/bin/python3 render_readme.py > README.md

venv:
	bash prepare_venv.sh

clean:
	rm -rf var/* .venv