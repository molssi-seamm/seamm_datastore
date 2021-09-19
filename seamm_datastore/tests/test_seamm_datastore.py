"""
Unit and regression test for the seamm_datastore package.
"""

# Import package, test suite, and other packages as needed
import pytest
import os

from dateutil import parser


def test_connected(connection):
    assert connection.current_user().username == "test_user"
    assert connection.default_project == "default"


def test_get_projects(connection):
    projects = connection.get_projects()
    assert len(projects) == 1


def test_connection_logout(connection):
    connection.logout()
    assert connection.current_user() is None


def test_add_job_error(connection):
    from seamm_datastore.util import LoginRequiredError
    connection.logout()
    with pytest.raises(LoginRequiredError):
        connection.add_job({"title": "fake job"})


def test_add_job(connection):
    from seamm_datastore.database.models import Project

    # Create a sample project
    test_project = {
        "name": "MyProject",
        "path": "test_project_path",
        "owner_id": 3,
        "id": 100,
    }

    project = Project(**test_project)

    job1_data = {
        "flowchart_id": "ABCD",
        "id": 1,
        "path": "a/path",
        "submitted": parser.parse("2016-08-29T09:12:33.001000+00:00"),
        "projects": [project],
        "owner_id": 3,
        "status": "finished",
        "title": "test job",
        "description": "",
    }
    connection.add_job(job1_data)

    # Retrieve job
    assert len(connection.get_jobs()) == 1
