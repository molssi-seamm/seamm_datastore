Getting Started
===============

This page details how to get started with seamm_datastore.

Flowchart formats
-----------------

The datastore records the flowchart of every job. It reads both SEAMM flowchart
formats: the JSON format 2.0, and the YAML format 3.0 that SEAMM writes from its
2026.10 releases on. A format 3.0 flowchart's metadata (title, description, creators
and so on) and its digests come from the file's ``metadata`` and ``digest`` sections.
Converting an installation's existing flowcharts to 3.0 is done by SEAMM itself
(``seamm-manager flowcharts migrate``), not by the datastore.

Rebuilding a datastore from the job directories
-----------------------------------------------

Each job directory holds the job's flowchart and a ``job_data.json``, which is what
the datastore records, so a datastore can be made again from the directories::

    import seamm_datastore

    result = seamm_datastore.build_from_jobs(
        "Jobs/seamm.db.new",             # the datastore to create; must not exist
        "Jobs/projects",                 # the projects and their jobs
        keep_from="Jobs/seamm.db",       # optional: the datastore being replaced
    )
    print(result["projects"], result["jobs"])

With ``keep_from``, the accounts (users, groups and roles), the details of projects
that still exist, and the owner and permissions of each job are kept from the old
datastore; without it, everything is owned by the user running the rebuild (or
``username``). Projects that a job lists but that do not exist yet are created.
``job_directories(projects_path)`` lists the job directories that would be read.

Users normally do this with ``seamm-manager datastore rebuild``, which stops the
services, keeps the accounts, and keeps the old datastore as a dated backup. The web
UI also builds a missing datastore from the job directories when it starts.
