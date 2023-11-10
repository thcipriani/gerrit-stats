SHELL := /bin/bash

all: clean data/last-update.txt data/repos.csv
	mkdir -p data
	< data/repos.csv parallel -d "\r\n" -C, 'bash 01-get-meta-refs.sh {1} {2} {3} "$(shell cat data/last-update.txt)"'
	bash _step-time.sh
	bash 02-get-all-known-reviewers.sh
	bash _step-time.sh
	python3 03-get-known-reviewers.py
	bash _step-time.sh
	< data/repos.csv parallel -d "\r\n" -C, 'python3 04-walk-repos.py --name {1} --safe-path {2} --repo {3} --new-shas "data/{2}-meta-refs.csv" --known-reviewers "data/{2}-known-reviewers.csv" --out-dir data'
	bash _step-time.sh
	bash 05-create-db.sh 'gerrit.db'
	bash _step-time.sh
	< <(ls data/*.db) bash 06-merge-dbs.sh 'gerrit.db'
	bash _step-time.sh
	echo 'select distinct author_id from changes where author_id not in (select id from authors);' | sqlite3 gerrit.db > data/author-ids.txt
	bash _step-time.sh
	python3 07-get-authors.py --author-file data/author-ids.txt --output-file data/authors.db
	bash _step-time.sh
	bash 08-add-user-table.sh 'gerrit.db' 'data/authors.db'
	bash _step-time.sh
	echo 'select date from changes order by date desc limit 1;' | sqlite3 gerrit.db > LAST_RUN

clean:
	rm -rf data
	mkdir -p data
	touch data/.gitkeep
	bash _step-time.sh

data/last-update.txt:
	mkdir -p data
	bash _step-time.sh
	if test -f LAST_RUN; then cat LAST_RUN > data/last-update.txt; else echo never > data/last-update.txt; fi

data/repos.csv:
	mkdir -p data
	bash _step-time.sh
	python3 00-get-repos.py "/srv/git" "/srv/git"
