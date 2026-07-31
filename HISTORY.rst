=======
History
=======
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
