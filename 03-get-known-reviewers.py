#!/usr/bin/env python

import sys
import os
import pandas as pd

from utils import make_safe_filename

ALL_REVIEWERS = 'data/all-known-reviewers.csv'
if not os.path.exists(ALL_REVIEWERS):
    print(f'File {ALL_REVIEWERS} not exist. Might be first run. Continuing...')
    sys.exit(0)

df = pd.read_csv(ALL_REVIEWERS, encoding='utf-8', index_col=0)
print(df.head())
df['safe_filename'] = df['repo'].apply(make_safe_filename)
for repo, group in df.groupby('repo'):
    filename = 'data/{}-known-reviewers.csv'.format(group['safe_filename'].iloc[0])
    print(f'Writing {repo} reviewers to {filename}')
    group.to_csv(filename, encoding='utf-8', index=False)
