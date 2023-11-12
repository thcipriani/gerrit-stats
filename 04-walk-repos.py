#!/usr/bin/env python

import argparse
import collections
import os
import re
import sqlite3
import sys

import pandas as pd

import pygit2

EMPTY_TREE_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
TRAILER_RE = re.compile(r'(?P<key>[a-zA-Z-_]+)+:\s?(?P<value>.*)')
LABEL_RE = re.compile(r''.join([
    r'([Pp]atch [Ss]et \d+:\s+(?P<label>[A-Za-z-]+)(?P<value>[+-]\d+)',
    r'|',
    r'[Pp]atch [Ss]et \d+:\s+(?P<oldlabel>[A-Za-z-]+))',
]))

def create_database(filename):
    conn = sqlite3.connect(filename)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY,
            repo TEXT NOT NULL,
            patchset INTEGER NOT NULL,
            patch INTEGER NOT NULL,
            sha TEXT NOT NULL,
            date INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            status TEXT,
            type TEXT NOT NULL,
            vote INTEGER,
            reviewer_id INTEGER,
            bot_like INTEGER NOT NULL
         )""")

    return conn

def save_change(commit, conn, repo_name):
    bot_like = 1 if commit.bot_like else 0
    conn.execute("""
        INSERT INTO changes (repo, patchset, patch, sha, date, author_id, type, status, vote, reviewer_id, bot_like)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (repo_name,
         commit.ps.patchset,
         commit.patch,
         commit.sha,
         commit.date,
         commit.author,
         commit.type,
         commit.status,
         commit.vote,
         commit.reviewer,
         bot_like))

def do_save(commits, conn, repo_name):
    for commit in commits:
        save_change(commit, conn, repo_name)

def get_commit_author_id(commit):
    try:
        return int(commit.author.email.split('@')[0])
    except ValueError as e:
        # TODO: Known problem emails
        # - gerrit@wikimedia.org
        # - server@googlesource.com
        # - ...probably any other repo we import from any other gerrit
        print(
            f'Non-numeric commit author: {commit.author.email}',
            file=sys.stderr
        )
        return 0


class Comments(object):
    def __init__(self, commit):
        self.commit = commit
        self.trailer_re = TRAILER_RE
        self.comment_label_re = LABEL_RE
        self._comment_labels = None
        self._patch = None
        self._comments = None
        self._trailers = None

    @property
    def trailers(self):
        """
        TODO: fix in pygit2
        """
        if self._trailers is None:
            self._trailers = {}
            rev_message = self.commit.message.splitlines()[::-1]
            for line in rev_message:
                if not line.strip():
                    break
                if ':' not in line:
                    continue
                m = self.trailer_re.match(line)
                if m:
                    if self._trailers.get(m['key'], None) is None:
                        self._trailers[m['key']] = m['value'].strip()
                    else:
                        self._trailers[m['key']] += '\n' + m['value'].strip()
        return self._trailers

    @property
    def has_real_comments(self):
        return len(self._patch_comments()) > 0

    @property
    def has_new_patch_comments(self):
        return len(self._newpatchpatchset_comments()) > 0

    @property
    def has_label_comments(self):
        return len(self.label_comments) > 0

    @property
    def label_comments(self):
        if self._comment_labels:
            return self._comment_labels

        self._comment_labels = []

        if not self._status_update_comments():
            return self._comment_labels

        known_labels = ['Verified', 'Code-Review', 'SUBM']
        for comment in self.comments:
            if not comment.lower().startswith('patch set %s:' % self.patch):
                continue

            # New style:
            #   Patch Set 1: Verified-1
            #   Patch Set 2: Code-Review+2
            # Or removing a label, old style:
            #   Patch Set 2: -Code-Review
            #   Patch Set 2: -Verified
            m = self.comment_label_re.match(comment)
            if m:
                if m.group('oldlabel'):
                    label = m.group('oldlabel')[1:]
                    value = 0
                elif m.group('label'):
                    label = m.group('label')
                    value = int(m.group('value'))
                if label in known_labels:
                    self._comment_labels.append((
                        label, value
                    ))
        return self._comment_labels

    @property
    def comments(self):
        if self._comments is None:
            self._comments = [
                l for l in self.commit.message.splitlines()
                if l.strip() and
                   l.split(':')[0] not in self.trailers
            ]
        return self._comments

    @property
    def is_status_update(self):
        return self._status_update_comments() != []

    @property
    def is_recheck(self):
        if not self.is_status_update:
            return False
        return [l for l
                in self._patch_comments()
                if l.lower().startswith('recheck')] != []

    @property
    def is_abandon(self):
        if not self.is_status_update:
            return False
        return [l for l
                in self._patch_comments()
                if l.lower().startswith('abandoned')] != []

    @property
    def is_rebase(self):
        if not self.has_new_patch_comments:
            return False

        return [l for l
                in self.comments
                if l.lower().endswith('rebased.')] != []

    @property
    def patch(self):
        if self._patch is None:
            patch = self.trailers.get(
                'Patch-set',
                self._patch_from_comments()
            )
            if patch is not None:
                try:
                    patch = int(patch)
                except ValueError:
                    # Happens when patch is like '1 (published)'
                    patch = int(patch.split(' ')[0])
            self._patch = patch
        return self._patch

    def _patch_from_comments(self):
        if not self.is_status_update:
            return None
        return self.commit.message.splitlines()[0].split(' ')[-1]

    def _newpatch_line(self, line):
        l = line.lower()
        return (l.startswith('create change') or
                l.startswith('uploaded patch set') or
                l.startswith('create patch set'))

    def _status_line(self, line):
        return line.lower().startswith('update patch set')

    def _status_update_comments(self):
        return [
            l for l in self.comments
            if self._status_line(l)
        ]

    def _newpatchpatchset_comments(self):
        return [
            l for l in self.comments
            if self._newpatch_line(l)
        ]

    def _patch_comments(self):
        """
        Real actual comments only
        """
        return [
            l for l in self.comments
            if (
                not self._newpatch_line(l)
                and not self._status_line(l)
            )
        ]


class MetaCommit(object):
    def __init__(self, commit):
        self.type = 'meta'
        self.vote = None
        self.commit = commit
        self.author = get_commit_author_id(commit)
        self.date = commit.author.time
        self.sha = commit.hex
        self.comments = Comments(commit)
        self.patch = self.get_patch()
        self.trailers = self.comments.trailers
        self.status = self.trailers.get('Status')
        self.reviewer = None
        self._votes = None

    @property
    def is_reviewer(self):
        reviewer = self.trailers.get('Reviewer', None)
        return reviewer is not None

    @property
    def is_label(self):
        has_label = self.trailers.get('Label', False)
        if not has_label:
            has_label = self.comments.has_label_comments
        return has_label

    @property
    def is_work_in_progress(self):
        """
        The default for new patches is WIP='false'

        We WIP on new patchsets if it's not the default, so 'true'
        We care about WIP on every other type, regardless
        """
        is_wip = self.trailers.get('Work-in-progress', None) is not None
        if not is_wip:
            return False

        default_wip = 'false'
        patch_wip = self.trailers.get('Work-in-progress', default_wip)
        new_patch = self.is_patch and self.patch == 1
        new_patch_with_default_state = new_patch and patch_wip == default_wip

        return is_wip and not new_patch_with_default_state

    @property
    def is_patch(self):
        is_ps = self.trailers.get('Patch-set', None) is not None
        return is_ps and \
            self.comments.has_new_patch_comments

    @property
    def is_comment(self):
        """
        Inline comments, but not a new patchset
        Or patch comments
        """
        return self.has_inline_comments() or \
            self.comments.has_real_comments

    @property
    def is_botlike(self):
        tag = self.trailers.get('Tag', None)
        if tag is None:
            return False
        if tag.startswith('autogenerated') and \
              not tag.endswith('abandon'):
            return True

    def get_patch(self):
        return self.comments.patch

    def make_comment(self, ps):
        if self.comments.is_recheck:
            return Recheck(self.commit, self, ps)
        if self.comments.is_abandon:
            return Abandon(self.commit, self, ps)
        return Comment(self.commit, self, ps)

    def make_work_in_progress(self, ps):
        return WorkInProgress(self.commit, self, ps)

    def make_patch(self, ps):
        if self.comments.is_rebase:
            return Rebase(self.commit, self, ps)
        if self.patch == 1:
            return NewPatchSet(self.commit, self, ps)
        return Patch(self.commit, self, ps)

    def make_reviewers(self, ps):
        for reviewer_id in self.get_reviewer_ids():
            if reviewer_id in ps.known_reviewers:
                continue
            yield Reviewer(self.commit, self, ps, reviewer_id)

    def get_votes(self):
        if self._votes:
            return self._votes
        if self.trailers.get('Label'):
            self._votes = [(l,v) for l,v in self._get_votes_from_label()]
        else:
            self._votes = self.comments.label_comments
        return self._votes

    def _get_votes_from_label(self):
        labels = self.trailers['Label'].splitlines()
        label_objs = []
        for label in labels:
            if label.startswith('-'):
                label = label[1:].split(' ')[0]
                vote = 0
            else:
                label, vote = label.split('=')
                # Got to handle:
                # - Label: Code-Review=+2
                # - Label: Code-Review=+2 Gerrit User <gerrit@wikimedia>
                vote = int(vote.split(' ')[0])
            yield label, vote

    def make_labels(self, ps):
        for label, vote in self.get_votes():
            if label == 'Code-Review':
                yield CodeReview(self.commit, self, ps, label, vote)
            elif label == 'Verified':
                yield Verified(self.commit, self, ps, label, vote)
            elif label == 'SUBM':
                yield Submit(self.commit, self, ps, label, vote)
            else:
                raise('Unknown label %s' % label)

    def has_inline_comments(self):
        return (
            self.has_updated_tree() and
            not self.comments.has_new_patch_comments
        )

    def get_reviewer_ids(self):
        reviewer_ids = []
        for reviewer in self.trailers['Reviewer'].splitlines():
            reviewer_ids.append(int(reviewer.split('<')[1].split('@')[0]))
        return reviewer_ids

    def has_updated_tree(self):
        parent_tree = EMPTY_TREE_SHA

        if self.commit.parents:
            parent_tree = self.commit.parents[0].tree.id

        return parent_tree != self.commit.tree.id

    def get_comments(self):
        return self.comments.comments

    def __repr__(self):
        return '<%s %s> by %s (%s)' % (
            self.type, self.patch, self.author, self.status
        )


class Reviewer(MetaCommit):
    def __init__(self, commit, mc, ps, reviewer_id):
        super(Reviewer, self).__init__(commit)
        self.type = 'reviewer'
        self.reviewer = reviewer_id
        self.label = mc.trailers.get('Label')
        self.message = mc.get_comments()
        self.mc = mc
        self.ps = ps
        self.bot_like = mc.is_botlike

    def __repr__(self):
        thing = '<Reviewer (%s %s)>' % (self.type, self.reviewer)
        thing += ' addedby %s' % self.author
        thing += ' (patch %s)' % self.patch
        thing += ' (status %s)' % self.status
        if self.bot_like:
            thing += ' (bot)'
        return thing

class WorkInProgress(MetaCommit):
    def __init__(self, commit, mc, ps):
        super(WorkInProgress, self).__init__(commit)
        self.type = 'wip'
        self.vote = 0 if mc.trailers['Work-in-progress'] == 'false' else 1
        self.label = mc.trailers.get('Label')
        self.message = mc.get_comments()
        self.mc = mc
        self.ps = ps
        self.bot_like = mc.is_botlike

class Comment(MetaCommit):
    def __init__(self, commit, mc, ps):
        super(Comment, self).__init__(commit)
        self.type = 'comment'
        self.reviewer = self.author
        self.status = mc.trailers.get('Status')
        self.label = mc.trailers.get('Label')
        self.message = mc.get_comments()
        self.mc = mc
        self.ps = ps
        self.bot_like = mc.is_botlike

    def __repr__(self):
        thing = '<Comment (%s)>' % self.type
        thing += ' addedby %s' % self.author
        thing += ' (patch %s)' % self.patch
        thing += ' (status %s)' % self.status
        if self.bot_like:
            thing += ' (bot)'
        return thing

class Recheck(Comment):
    def __init__(self, commit, mc, ps):
        super(Recheck, self).__init__(commit, mc, ps)
        self.type = 'recheck'

class Abandon(Comment):
    def __init__(self, commit, mc, ps):
        super(Abandon, self).__init__(commit, mc, ps)
        self.type = 'abandon'

class Label(MetaCommit):
    def __init__(self, commit, mc, ps, label, vote):
        super(Label, self).__init__(commit)
        self.type = 'label'
        self.reviewer = self.author
        self.status = mc.trailers.get('Status')
        self.label = label
        self.message = mc.get_comments()
        self.mc = mc
        self.ps = ps
        self.bot_like = mc.is_botlike
        self.vote = vote
        self.type = '?'

class CodeReview(Label):
    def __init__(self, commit, mc, ps, label, vote):
        super(CodeReview, self).__init__(commit, mc, ps, label, vote)
        self.type = 'codereview'

    def __repr__(self):
        return '<CodeReview %s> by %s (%s)' % (
            self.vote, self.author, self.status)

class Verified(Label):
    def __init__(self, commit, mc, ps, label, vote):
        super(Verified, self).__init__(commit, mc, ps, label, vote)
        self.type = 'verified'

    def __repr__(self):
        return '<Verified %s> by %s (%s)' % (
            self.vote, self.author, self.status)

class Submit(Label):
    def __init__(self, commit, mc, ps, label, vote):
        super(Submit, self).__init__(commit, mc, ps, label, vote)
        self.type = 'submit'

    def __repr__(self):
        return '<Submit %s> by %s (%s)' % (
            self.vote, self.author, self.status)

class Patch(MetaCommit):
    def __init__(self, commit, mc, ps):
        super(Patch, self).__init__(commit)
        self.type = 'patch'
        self.patch = mc.comments.patch
        self.status = mc.trailers.get('Status')
        self.change_id = mc.trailers.get('Change-id')
        self.target_branch = mc.trailers.get('Branch')
        self.owner_id = self.author
        self.subject = mc.trailers.get('Subject')
        self.mc = mc
        self.ps = ps
        self.bot_like = False

class Rebase(Patch):
    def __init__(self, commit, mc, ps):
        super(Rebase, self).__init__(commit, mc, ps)
        self.type = 'rebase'

class NewPatchSet(Patch):
    def __init__(self, commit, mc, ps):
        super(NewPatchSet, self).__init__(commit, mc, ps)
        self.type = 'newpatchset'
        self.status = 'new'

class Patchset(object):
    def __init__(self, repo, ref):
        self.repo = repo
        self.ref = ref
        self.sha = ref.target.hex
        self.patchset = int(ref.name.split('/')[3])
        self.patchset_ref = ref.name
        self.known_reviewers = set()
        self.commits = []
        self.patches = []

    def known_reviewer(self, reviewers):
        for reviewer in reviewers:
            if reviewer.reviewer in self.known_reviewers:
                return True
            self.known_reviewers.add(reviewer.reviewer)
        return False

    def walk(self, unknown):
        """
        Each commit is either:
        - A patch
        - A comment
        - Adds several labels
        - Adds several reviewers
        """
        for commit in self.repo.walk(self.ref.target, pygit2.GIT_SORT_REVERSE):
            # 0 will only be here if it's the first time we've run this
            if 0 not in unknown and commit.hex not in unknown:
                continue
            mc = MetaCommit(commit)
            # print('    - Processing commit %s' % mc.sha)
            if mc.is_patch:
                patch = mc.make_patch(self)
                self.patches.append(patch)
                self.commits.append(patch)

            if mc.is_reviewer:
                for reviewer in mc.make_reviewers(self):
                    self.commits.append(reviewer)
                    self.known_reviewers.add(reviewer.reviewer)

            if mc.is_work_in_progress:
                self.commits.append(mc.make_work_in_progress(self))

            # Labels > Comments
            # show it as a label, even if there are comments
            if mc.is_label:
                for label in mc.make_labels(self):
                    self.commits.append(label)
                    self.known_reviewers.add(label.author)
            elif mc.is_comment:
                comment = mc.make_comment(self)
                self.commits.append(comment)
                self.known_reviewers.add(comment.author)

        yield self.commits

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', help='Name of the repo')
    ap.add_argument('--repo', help='Path to the repo')
    ap.add_argument('--new-shas', help='csv of new shas')
    ap.add_argument('--known-reviewers', help='csv of known reviewers')
    ap.add_argument('--safe-path', help='safe path name for db')
    ap.add_argument('--out-dir', help='where to put the output')
    return ap.parse_args()

def main():
    args = parse_args()
    conn = create_database(f"{args.out_dir}/{args.safe_path}.db")
    conn.execute("BEGIN TRANSACTION")
    repo = pygit2.Repository(args.repo)
    df = pd.read_csv(args.new_shas)
    # Get known shas from the csv, grouped by individual ref names
    print('Processing %s' % args.name)
    known_shas = df.groupby('refname')['commit'].apply(list).to_dict()
    if os.path.isfile(args.known_reviewers):
        df_reviewers = pd.read_csv(args.known_reviewers)
        known_reviewers = df_reviewers.groupby('patchset')['author_id'].apply(set).to_dict()
    else:
        known_reviewers = {}
    for ref, known in known_shas.items():
        print('Processing %s - %s' % (args.name, ref))
        count = 0
        ps = Patchset(repo, repo.lookup_reference(ref))
        ps.known_reviewers = known_reviewers.get(ps.patchset, set())
        for commit in ps.walk(set(known)):
            if not commit:
                print(f'    - Empty commit for {ref}')
                # This happens if someone does something with attentionsets
                # Which we don't track...
                continue
            if isinstance(commit, list):
                for c in commit:
                    print('    - %s' % c)
            else:
                print('    - %s' % commit)
            do_save(commit, conn, args.name)
            if count % 100 == 0:
                print('Committing changes')
                conn.commit()
                conn.execute("BEGIN TRANSACTION")
            del commit  # Neeed to free memory...
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
