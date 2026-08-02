"""
Tests for building/importing datastore
"""

import os


def test_build(connection):
    from seamm_datastore.database.models import Flowchart

    loc = os.path.abspath(os.path.dirname(__file__))
    added_jobs, added_projects = connection.import_datastore(
        os.path.join(loc, "..", "data", "Projects")
    )

    flowcharts = Flowchart.permissions_query(permission="read").all()

    assert len(added_jobs) == 2
    assert len(added_projects) == 1, added_projects
    assert len(flowcharts) == 1


def test_import_datastore_duplicate_project_name_recovers(connection, tmp_path):
    """A job_data.json listing the same project twice (a real case seen in
    production -- e.g. from a job submitted with a malformed project list)
    used to crash the whole import scan with an IntegrityError ("UNIQUE
    constraint failed: job_project.job, job_project.project"), raised from
    session.commit() in import_datastore. That commit sat in an `else:`
    clause the surrounding try/except couldn't reach, so the failure
    propagated out of import_datastore entirely -- aborting the scan and
    leaving every job after the bad one (in directory-listing order)
    unimported too, every time the dashboard started.

    Fixed two ways: Job.create() now dedupes project_names before it's used
    to populate any relationship (the actual root cause -- assigning the
    same related row twice to a SQLAlchemy many-to-many collection is what
    raises the IntegrityError), and import_datastore's per-job add()/commit()
    is now inside the try/except with a rollback, so even an unrelated
    per-job failure can no longer take down the whole scan.
    """
    import json
    import shutil
    from pathlib import Path

    import seamm_datastore

    sample = Path(seamm_datastore.__file__).parent / "data" / "sample_flowchart_v2.flow"
    projects_dir = tmp_path / "Projects"

    def make_job(job_id, projects):
        job_dir = projects_dir / "default" / f"Job_{job_id:06d}"
        job_dir.mkdir(parents=True)
        shutil.copy(sample, job_dir / "flowchart.flow")
        job_data = {
            "data_version": "1.0",
            "command line": [],
            "title": f"job {job_id}",
            "working directory": str(job_dir),
            "state": "submitted",
            "projects": projects,
            "datastore": str(tmp_path),
            "job id": job_id,
        }
        with (job_dir / "job_data.json").open("w") as fd:
            fd.write("!MolSSI job_data 1.0\n")
            json.dump(job_data, fd)

    # The bad job: "default" listed twice.
    make_job(1, ["default", "default"])
    # A second, otherwise-normal job in the same scan -- must still import
    # even though it's processed after the bad one.
    make_job(2, ["default"])

    jobs, _ = connection.import_datastore(str(projects_dir))

    ids = {j["id"] for j in jobs}
    assert 1 in ids, "job with a duplicated project name should still import"
    assert 2 in ids, "a later job in the same scan must not be skipped"
