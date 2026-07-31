"""
Test the create functions on the SQLAlchemy models
"""

import os

import pytest


def test_project_create(connection):
    """Test the create method of the project object"""

    project = connection.Project.create(name="test_project")

    assert project.name == "test_project"
    assert project.owner == connection.current_user()

    # If group is not specified, the group should be the
    # first group the user belongs to.
    assert project.group.name == connection.current_user().groups[0].name


def test_project_exists(connection):
    with pytest.raises(ValueError):
        connection.Project.create(name="default")


def test_project_no_user(connection):
    with pytest.raises(ValueError):
        connection.logout()
        connection.Project.create(name="test")


def test_project_create_group(connection):
    project = connection.Project.create(name="test_project", group="admin")

    assert project.name == "test_project"
    assert project.owner == connection.current_user()

    assert project.group.name == "admin"


def test_flowchart_parse(connection):
    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    metadata, text = connection.Flowchart.parse_flowchart_file(filepath)

    assert metadata["flowchart_version"] == 2.0
    assert (
        metadata["sha256_strict"]
        == "79d580b78559fe137872bcffe24aa7455e6c66fe260cf63e5edd3b3a1464e9c6"
    )

    assert text


def test_flowchart_from_file(connection):
    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    flowchart = connection.Flowchart.create_from_file(filepath)

    assert (
        flowchart.sha256_strict
        == "79d580b78559fe137872bcffe24aa7455e6c66fe260cf63e5edd3b3a1464e9c6"
    )


def test_create_user(connection):
    user = connection.User.create(username="test", password="test")

    assert user.username == "test"
    assert user.groups[0].name == user.username


def test_flowchart_duplicate_hash_raises(connection):
    """Directly re-creating the same flowchart via `create` is still an error."""
    from seamm_datastore import session_scope

    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    with session_scope(connection.Session) as sess:
        sess.add(connection.Flowchart.create_from_file(filepath))

    with pytest.raises(ValueError):
        connection.Flowchart.create_from_file(filepath)


def test_flowchart_sha256_strict_unique_constraint(connection):
    """The DB itself must reject a second flowcharts row for the same hash.

    This is the schema-level half of the fix for
    https://github.com/molssi-seamm/seamm_datastore/issues/37 : previously
    nothing stopped two rows from sharing a ``sha256_strict``, which is what
    let the concurrent-submission race described in the issue corrupt the
    table in the first place.
    """
    from sqlalchemy.exc import IntegrityError
    from seamm_datastore import session_scope
    from seamm_datastore.database.models import Flowchart

    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    metadata, flowchart_json = Flowchart.parse_flowchart_file(filepath)

    with session_scope(connection.Session) as sess:
        sess.add(
            Flowchart(
                sha256_strict=metadata["sha256_strict"],
                sha256=metadata["sha256"],
                json=flowchart_json,
            )
        )

    with pytest.raises(IntegrityError):
        with session_scope(connection.Session) as sess:
            sess.add(
                Flowchart(
                    sha256_strict=metadata["sha256_strict"],
                    sha256=metadata["sha256"],
                    json=flowchart_json,
                )
            )


def test_flowchart_get_or_create_concurrent_race(tmp_path):
    """A get-or-create that loses a race to another job's commit must fall
    back to the winner's row instead of crashing.

    Reproduces https://github.com/molssi-seamm/seamm_datastore/issues/37 : a
    job array submitting several jobs that share a flowchart which isn't
    registered yet. Each sees "no flowchart with this hash" and races to
    insert it; before this fix, every insert after the first left a
    duplicate row, and every later lookup by hash crashed with
    MultipleResultsFound.

    The race is reproduced deterministically -- a competing row for the same
    hash is committed by a second, raw connection to the same database file,
    timed to land in the window between our own lookup and our own insert --
    rather than depending on real thread scheduling, which is flaky against
    SQLite's single-writer locking.
    """
    import sqlite3

    import seamm_datastore

    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    db_path = tmp_path / "race.db"
    db = seamm_datastore.connect(database_uri=f"sqlite:///{db_path}", initialize=True)
    db.login(username="admin", password="admin")

    # `seamm_datastore.database.models` (and the flask_authorize patch it
    # loads) must not be imported before the first `connect()` call sets up
    # the fake app config the patch relies on -- so import it only now.
    from seamm_datastore.database.models import Flowchart

    metadata, flowchart_json = Flowchart.parse_flowchart_file(filepath)
    sha256_strict = metadata["sha256_strict"]

    original_parse = Flowchart.parse_flowchart_file
    call_count = 0

    def racy_parse(path):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            # `get_or_create_from_file` has already looked up this hash and
            # found nothing (call #1, above) and is about to build its own
            # row (this is the second parse, from inside `create_from_file`
            # in the nested-transaction attempt) -- commit a competitor now,
            # simulating another job's insert winning the race.
            raw = sqlite3.connect(str(db_path))
            raw.execute(
                "INSERT INTO flowcharts (sha256_strict, json) VALUES (?, ?)",
                (sha256_strict, flowchart_json),
            )
            raw.commit()
            raw.close()
        return original_parse(path)

    Flowchart.parse_flowchart_file = staticmethod(racy_parse)
    try:
        with seamm_datastore.session_scope(db.Session) as sess:
            flowchart = Flowchart.get_or_create_from_file(filepath)
            sess.add(flowchart)
            flowchart_id = flowchart.id
    finally:
        Flowchart.parse_flowchart_file = staticmethod(original_parse)

    assert flowchart_id is not None

    # Only one flowchart row should exist for this hash despite the race.
    with seamm_datastore.session_scope(db.Session) as sess:
        rows = sess.query(Flowchart).filter_by(sha256_strict=sha256_strict).all()
        assert len(rows) == 1
        assert rows[0].id == flowchart_id


def test_job_create_shared_flowchart_reuses_row(connection):
    """Two jobs that use the same flowchart file must share one Flowchart row."""
    from pathlib import Path

    path = (
        Path(__file__)
        / ".."
        / ".."
        / "data"
        / "Projects"
        / "sample_project1"
        / "Job_000093"
    )
    path = path.expanduser().resolve()
    flowchart_filename = str(path / "flowchart.flow")

    job1 = connection.Job.create(
        id=1,
        flowchart_filename=flowchart_filename,
        project_names=["default"],
    )
    job2 = connection.Job.create(
        id=2,
        flowchart_filename=flowchart_filename,
        project_names=["default"],
    )

    assert job1.flowchart is job2.flowchart


def test_add_job(connection):
    from pathlib import Path
    from dateutil import parser

    from seamm_datastore import session_scope

    path = (
        Path(__file__)
        / ".."
        / ".."
        / "data"
        / "Projects"
        / "sample_project1"
        / "Job_000093"
    )
    path = path.expanduser().resolve()

    job_data = dict(
        id=1,
        flowchart_filename=str(path / "flowchart.flow"),
        project_names=["default"],
        path=str(path),
        title="test job",
        description="description of the job",
        submitted=parser.parse("2016-08-29T09:12:33.000000+00:00"),
        started=parser.parse("2016-08-29T09:12:34.000000+00:00"),
        finished=parser.parse("2016-08-29T09:13:34.000000+00:00"),
        status="finished",
        parameters={"job": "parameter"},
    )

    job = connection.Job.create(**job_data)

    assert job.id == 1

    expected = dict(
        id=1,
        path=str(path),
        title="test job",
        description="description of the job",
        status="finished",
        parameters={"job": "parameter"},
    )

    # Retrieve job
    with session_scope(connection.Session) as sess:
        from seamm_datastore.database.models import Job

        sess.add(job)
        sess.commit()
        jobs = sess.query(Job).all()
        assert len(jobs) == 1

        # Check the data - add times later
        for k, v in expected.items():
            assert getattr(job, k) == v
