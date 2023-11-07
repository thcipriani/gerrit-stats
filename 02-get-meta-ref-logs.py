#!/usr/bin/env python3
import pygit2
import csv
import sys

with open(sys.argv[1], 'r') as f:
    reader = csv.reader(f)
    commits = list(reader)
