#!/usr/bin/env python

import multiprocessing
import argparse
import requests
import json
import sqlite3

# Initialize a requests session
SESSION = requests.Session()

def create_db(output_file):
    conn = sqlite3.connect(output_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE authors (
              id integer primary key,
              username text not null,
              is_wmf integer not null,
              was_wmf integer not null,
              is_wmde integer not null,
              was_wmde integer not null)''')
    conn.commit()
    return conn

class Author(object):
    def __init__(self, author_id, emails, username, is_wmf, was_wmf, is_wmde, was_wmde):
        self.id = author_id
        self.emails = emails
        self.username = username
        self.is_wmf = is_wmf
        self.was_wmf = was_wmf
        self.is_wmde = is_wmde
        self.was_wmde = was_wmde

def get_author(author):
    print(f"Getting author...'{author}'")
    try:
        response = SESSION.get(f"https://gerrit.wikimedia.org/r/a/accounts/{author}/detail", auth=())
        response.raise_for_status()
        details = json.loads(response.text[5:])
    except requests.exceptions.HTTPError as e:
        print(f"Error getting author: {e}")
        return None

    try:
        response = SESSION.get(f"https://gerrit.wikimedia.org/r/a/accounts/{author}/groups", auth=())
        response.raise_for_status()
        groups = json.loads(response.text[5:])
    except requests.exceptions.HTTPError as e:
        print(f"Error getting author: {e}")
        return None

    is_wmf = 'ldap/wmf' in set([group['name'] for group in groups])
    is_wmde = 'ldap/wmde' in set([group['name'] for group in groups])

    email = '?'
    secondary_emails = []
    if details.get('email') is not None:
        email = details['email']
    if details.get('secondary_emails') is not None:
        secondary_emails = details['secondary_emails']

    emails = [email] + secondary_emails
    was_wmf = not not [email for email in emails if email.endswith("@wikimedia.org")]
    was_wmde = not not [email for email in emails if email.endswith("@wikimedia.de")]
    return Author(details["_account_id"], emails, details["username"], is_wmf, was_wmf, is_wmde, was_wmde)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--author-file", required=True, help="path to authors file")
    ap.add_argument("-o", "--output-file", required=True, help="path to output file")
    args = ap.parse_args()
    conn = create_db(args.output_file)

    with open(args.author_file, "r") as author_file:
        authors = author_file.read().splitlines()

    num_processes = multiprocessing.cpu_count()
    chunk_size = 50 # len(authors) // num_processes
    data_chunks = [authors[i:i + chunk_size] for i in range(0, len(authors), chunk_size)]
    for chunk in data_chunks:
        print(f"Chunk size: {len(chunk)}")
        pool = multiprocessing.Pool()
        authors = pool.map(get_author, chunk)
        authors = [a for a in authors if a is not None]
        conn.execute('BEGIN TRANSACTION')
        conn.executemany('INSERT INTO authors VALUES (?,?,?,?,?,?)', [
            (
                author.id,
                author.username,
                author.is_wmf,
                author.was_wmf,
                author.is_wmde,
                author.was_wmde
            ) for author in authors
        ])
        conn.commit()
        print(f"Inserted {len(authors)} authors")
    conn.close()

if __name__ == "__main__":
    main()
