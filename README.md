README for gerrit-stats
=======================

This is a simple tool to generate statistics from Wikimedia's Gerrit server.

Usage
-----

Setup a local clone of every public repo on gerrit.wikimedia.org.

I use the [myrepos][mr] tool `mr` to do this:

First I create an .mrconfig file:

    mkdir -p /srv/git
    cp ./_setup-srv_git.sh /srv/git/update.sh
    cd /srv/git
    ./update.sh

This clones all reapos from gerrit.wikimedia.org into `/srv/git`. It's going
to take some time.

Then inside this repo run make:

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
3. `02-get-all-known-reviewers.sh` Looks at the existing database and
   queries gerrit for all known reviewers. It outputs a csv of all known
   reviewers with repos and patchsets.
4. `03-get-known-reviewers.py` Creates per-repo known reviewers for use in
   the next step.
3. `04-walk-repos.py` takes a csv of repos, and the csv of refs, and
   outputs a sqlite database of all patches, reviewer adds, comments, and
   label votes (e.g., "Code-Review=+2")
4. `05-create-db.sh` creates a single sqlite database that has the same
   schema as the individual databases created by `03-walk-repos.py`.
5. `06-merge-dbs.sh` mashes together all the individual databases into a
   single database.
6. `07-get-author-ids.sh` queries the database for all author ids that are
   not already known.
6. `08-get-authors.py` takes all the author ids and queries gerrit in batches
   of 50 to get the author's username. It outputs a database of authors and
   their affiliation (`is_wmf`, `is_wmde`, `was_wmf`, `was_wmde`—it's not perfect).
7. `09-add-user-table.sh` adds new users to the `gerrit.db` database.

TODO
----

* Take reviewer and owner ids from gerrit and map to usernames in a new users table.
* Add a `06-stats.py` that generates interesting stats from the database

Oddities
--------

- New patches by jenkins-bot are rebases

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

Reviewer load by repo:

    select
        repo, count(distinct author_id) as count
    from changes
    where type = 'codereivew'
        and vote = 2
    group by repo
    order by count desc;

Patchsets by volunteers(-ish) folks +2'd by non-volunteer(-ish) folks:

    WITH earliest_patch AS (
      SELECT
        patchset AS epatchset,
        authors.username AS patch_author
      FROM
        changes
        JOIN authors ON changes.author_id = authors.id
      WHERE
        type = 'newpatchset'
        AND authors.is_wmf = 0
        AND authors.was_wmf = 0
        AND authors.is_wmde = 0
        AND authors.was_wmde = 0
        AND status = 'new'
        AND repo LIKE 'mediawiki/%'
      GROUP BY
        patchset
        ORDER BY date
    )
    SELECT
      repo,
      patch_author,
      'https://gerrit.wikimedia.org/r/' || patchset as url,
      username as reviewer,
      label,
      value,
      strftime('%Y', datetime(date, 'unixepoch')) AS year,
      strftime('%m', datetime(date, 'unixepoch')) AS month
    FROM
      changes
      JOIN authors ON changes.author_id = authors.id
      JOIN earliest_patch ON changes.patchset = earliest_patch.epatchset
    WHERE
      strftime('%Y', datetime(date, 'unixepoch')) = '2023'
      AND strftime('%m', datetime(date, 'unixepoch')) IN ('07', '08', '09')
      AND type = 'codereview'
      AND vote = 2
      AND (authors.is_wmf = 1 or authors.is_wmde = 1);

Patchsets per repo per year:

    SELECT
      repo,
      strftime('%Y', datetime(date, 'unixepoch')) AS year,
      count(*) as count
    FROM
      changes
    WHERE
      type = 'newpatchset'
    GROUP BY
      repo,
      year
    ORDER BY
      repo,
      year;

Average days to first review by repo:

    WITH earliest_patch AS (
      SELECT
        patchset AS epatchset,
        authors.username AS patch_author,
        MIN(date) AS upload_date
      FROM
        changes
        JOIN authors ON changes.author_id = authors.id
      WHERE
        type = 'newpatchset'
      GROUP BY
        patchset
      ORDER BY
        upload_date
    ),
    reviews AS (
      SELECT
        repo,
        patchset,
        patch_author,
        authors.username AS reviewer,
        type,
        vote,
        upload_date,
        MIN(date) AS review_date
      FROM
        changes
        JOIN authors ON changes.author_id = authors.id
        JOIN earliest_patch ON changes.patchset = earliest_patch.epatchset
      WHERE
        (
          /* Code-Review */
          (type = 'codereview')
          OR
          /* Comment */
          (type = 'comment')
        )
        /*jenkins-bot*/
        AND author_id != 75
        /*pipelinebot*/
        and author_id != 6784
        /*trainbranchbot*/
        and author_id != 7647
        /*l10n-bot*/
        and author_id != 137
        AND reviewer != patch_author
      GROUP BY
        changes.patchset
    )
    SELECT
      repo,
      AVG(review_date - upload_date) / (24 * 60 * 60) AS average_days_to_first_review
    FROM
      reviews
    group by repo
    order by
      average_days_to_first_review;

[mr]: http://myrepos.branchable.com/
