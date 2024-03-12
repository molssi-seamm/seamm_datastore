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
    assert user.groups[0].name == connection.default_group


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
