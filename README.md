README for gerrit-stats
=======================

This is a simple tool to generate statistics from Wikimedia's Gerrit server.

Usage
-----

Setup a local clone of every public repo on gerrit.wikimedia.org.

I use the [myrepos][mr] tool `mr` to do this:

First I create an .mrconfig file:

    cd /srv/git
    ./000-setup-srv_git.sh

Then run make:

    make

How it works
------------

This is a terrible local hadoop using gnu parallel and a bunch of shell scripts.

1. `00-get-repos.py` takes a base path and a search path. It outputs a csv
   of all git repos in the search path and safe file names based on the
   repo name (without the base path).
2. `01-get-meta-refs.sh` takes a csv of repos and outputs a csv of all
   `refs/changes/*/*/meta` refs in the repos. On subsequent runs, it will
   gather all changes since the last run for each ref. On the first run,
   it will only gather refs.
3. `03-walk-repos.py` takes a csv of repos, and the csv of refs, and
   outputs a sqlite database of all patches, reviewer adds, comments, and
   label votes (e.g., "Code-Review=+2")
4. `04-create-db.sh` creates a single sqlite database that has the same
   schema as the individual databases created by `03-walk-repos.py`.
5. `05-merge-dbs.sh` mashes together all the individual databases into a
   single database.

TODO
----

* Take reviewer and owner ids from gerrit and map to usernames in a new users table.
* Add a `06-stats.py` that generates interesting stats from the database

Fun queries
-----------

Time to merge:

    with mergedchanges as (
        select
            patchset, patch, date
        from changes
        where status = 'merged'
    ) select
        c.repo, c.patchset, m.patch, m.date - min(c.date) as ttm
    from changes c
    join mergedchanges m on m.patchset = c.patchset
    group by c.patchset
    order by ttm;

Biggest +2er by repo:

    select
        repo, author_id, count(*) as count
    from changes
    where type = 'label'
        and label = 'c'
        and value = 2
    group by repo, reviewer
    order by count desc;


[mr]: http://myrepos.branchable.com/
