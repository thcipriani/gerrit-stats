SHELL := /bin/bash

all: clean data/last-update.txt data/repos.csv
	mkdir -p data
	< data/repos.csv parallel -d "\r\n" -C, 'bash 01-get-meta-refs.sh {1} {2} {3} "$(shell cat data/last-update.txt)"'
	< data/repos.csv parallel -d "\r\n" -C, 'python3 03-walk-repos.py --name {1} --safe-path {2} --repo {3} --new-shas "data/{2}-meta-refs.csv" --out-dir data'
	bash 04-create-db.sh 'gerrit.db'
	< <(ls data/*.db) bash 05-merge-dbs.sh 'gerrit.db'
	date +%Y-%m-%d > LAST_RUN

clean:
	rm -rf data
	mkdir -p data
	touch data/.gitkeep

data/last-update.txt:
	mkdir -p data
	if test -f LAST_RUN; then cat LAST_RUN > data/last-update.txt; else echo never > data/last-update.txt; fi

data/repos.csv:
	mkdir -p data
	python3 00-get-repos.py "/srv/git" "/srv/git"
