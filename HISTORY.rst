=======
History
=======
2026.9.25 -- Bugfix: alembic is now a declared dependency
    * The database migration scripts import alembic, which the installer runs when
      updating the datastore, but it was not listed as a requirement. It is now.
    * ``make test`` now runs the package's tests directory only. Walking the whole
      package for doctests imported the alembic environment script, which fails
      outside alembic, and then ran the tests without a Flask application context.

2026.8.2 -- Bugfix: crash on a job with a duplicated project name
    * A job whose data listed the same project twice (for example
      ``"projects": ["default", "default"]``) made the datastore try to
      register that job-project link twice, crashing with a database
      integrity error. Because of where that crash happened, it could also
      abort an entire startup scan of the job directories, leaving every
      later job in that scan unimported too, on every restart. Duplicate
      project names are now silently ignored, and a failure importing one
      job no longer stops the rest from being imported.

2026.7.31 -- Bugfix: duplicate flowchart rows from concurrent job submission
    * Jobs sharing the same flowchart submitted at nearly the same time -- for
      example a job array -- could race past the check for whether the
      flowchart was already registered, each inserting its own copy. Once
      that happened, every later job submission crashed outright instead of
      finding the existing flowchart. The datastore now guards against this
      at the database level and falls back to the winning job's row instead
      of failing. A migration cleans up any duplicate rows already created by
      this bug in existing datastores.

2026.7.15 -- Bugfix: avoid "database is locked" errors under concurrent access
    * When many jobs accessed the datastore at the same time -- for example a
      batch of jobs submitted together on a cluster -- registering a job could
      fail immediately with "database is locked". The datastore now waits a
      short, configurable time for the database to become free and retries, so
      concurrent jobs register reliably. The wait time defaults to 20 seconds.
