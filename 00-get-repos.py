#!/usr/bin/env python

import argparse
import csv
import subprocess

def get_git_dirs(root_directory):
    command = ['find', root_directory, '-name', '*.git', '-type', 'd']
    find_cmd = subprocess.run(command, stdout=subprocess.PIPE, text=True)
    return find_cmd.stdout.splitlines()

def get_repo_name(base_path, git_dir):
    return git_dir[len(base_path) + 1:-4]

def make_safe_filename(repo_path):
    return repo_path.strip('/').replace('/', '_').replace('.', '_').replace(':', '_')

def parse_args():
    parser = argparse.ArgumentParser(
        description='Extract commit info and trailers from Gerrit')
    parser.add_argument('base_path', help='Path to the base directory')
    parser.add_argument('repo_path', help='Path to the git repository')
    return parser.parse_args()

def main():
    args = parse_args()
    repo_path = args.repo_path
    if repo_path.endswith('.git'):
        git_dirs = [repo_path]
    else:
        git_dirs = get_git_dirs(repo_path)

    print('Found {} git directories'.format(len(git_dirs)))
    with open('data/repos.csv', 'w') as f:
        writer = csv.writer(f)
        # writer.writerow(['repo', 'path', 'safe_path'])
        for git_dir in git_dirs:
            repo_name = get_repo_name(args.base_path, git_dir)
            safe_path = make_safe_filename(repo_name)
            writer.writerow([repo_name, safe_path, git_dir])
    print('Wrote data/repos.csv')

if __name__ == '__main__':
    main()
