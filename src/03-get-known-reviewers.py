#!/usr/bin/env python

import sys
import os
import pandas as pd

from utils import make_safe_filename

ALL_REVIEWERS = 'data/all-known-reviewers.csv'

# It shouldn't exist on the first run.
# It may exist if this is a subsequent run.
# But unless it ran most of the way through, it's probably empty
if not os.path.exists(ALL_REVIEWERS) or os.path.getsize(ALL_REVIEWERS) == 0:
    print(f'File {ALL_REVIEWERS} not exist. Might be first run. Continuing...')
    sys.exit(0)

df = pd.read_csv(ALL_REVIEWERS, encoding='utf-8', index_col=0)
print(df.head())
df['safe_filename'] = df['repo'].apply(make_safe_filename)
for repo, group in df.groupby('repo'):
    filename = 'data/{}-known-reviewers.csv'.format(group['safe_filename'].iloc[0])
    print(f'Writing {repo} reviewers to {filename}')
    group.to_csv(filename, encoding='utf-8', index=False)
