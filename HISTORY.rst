=======
History
=======
2026.7.15 -- Bugfix: avoid "database is locked" errors under concurrent access
    * When many jobs accessed the datastore at the same time -- for example a
      batch of jobs submitted together on a cluster -- registering a job could
      fail immediately with "database is locked". The datastore now waits a
      short, configurable time for the database to become free and retries, so
      concurrent jobs register reliably. The wait time defaults to 20 seconds.
