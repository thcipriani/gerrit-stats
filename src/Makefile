SHELL := /bin/bash

all: clean data/last-update.txt data/repos.csv
	mkdir -p data
	@bash _step-time.sh | tee -a data/step-times.txt
	< data/repos.csv parallel -d "\r\n" -C, 'bash 01-get-meta-refs.sh {1} {2} {3} "$(shell cat data/last-update.txt)"'
	@bash _step-time.sh | tee -a data/step-times.txt
	bash 02-get-all-known-reviewers.sh
	@bash _step-time.sh | tee -a data/step-times.txt
	python3 03-get-known-reviewers.py
	@bash _step-time.sh | tee -a data/step-times.txt
	< data/repos.csv parallel -d "\r\n" -C, 'python3 04-walk-repos.py --name {1} --safe-path {2} --repo {3} --new-shas "data/{2}-meta-refs.csv" --known-reviewers "data/{2}-known-reviewers.csv" --out-dir data 2> data/{2}-error.log'
	@bash _step-time.sh | tee -a data/step-times.txt
	bash 05-create-db.sh 'gerrit.db'
	@bash _step-time.sh | tee -a data/step-times.txt
	< <(ls data/*.db) bash 06-merge-dbs.sh 'gerrit.db'

authors: gerrit.db
	@bash _step-time.sh | tee -a data/step-times.txt
	bash 07-get-author-ids.sh 'gerrit.db'
	@bash _step-time.sh | tee -a data/step-times.txt
	python3 08-get-authors.py --author-file data/author-ids.txt --output-file data/authors.db
	@bash _step-time.sh | tee -a data/step-times.txt
	bash 09-add-user-table.sh 'gerrit.db' 'data/authors.db'
	@bash _step-time.sh | tee -a data/step-times.txt
	echo 'select date from changes order by date desc limit 1;' | sqlite3 gerrit.db > LAST_RUN

deployment: gerrit.db
	bash 10-add-deployment-table.sh 'gerrit.db' 'train-stats/data/train.db'

logfile: gerrit.db
	# database, output file, start date, end date
	bash 11-generate-log.sh gerrit.db log-$(shell date -I)-10.csv 2021-01-01 $(shell date -I)
	bash 12-clean-log.sh log-$(shell date -I)-10.csv

clean:
	rm -rf data/*.db data/*.csv data/*.log data/*.txt
	mkdir -p data
	touch data/.gitkeep
	@bash _step-time.sh | tee -a data/step-times.txt

data/last-update.txt:
	mkdir -p data
	@bash _step-time.sh | tee -a data/step-times.txt
	if test -f LAST_RUN; then cat LAST_RUN > data/last-update.txt; else echo never > data/last-update.txt; fi

data/repos.csv:
	mkdir -p data
	@bash _step-time.sh | tee -a data/step-times.txt
	python3 00-get-repos.py "/srv/git" "/srv/git"
