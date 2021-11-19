"""
Unit and regression test for the seamm_datastore package.
"""

# Import package, test suite, and other packages as needed
from pathlib import Path
import pprint
import pytest

from dateutil import parser


def test_connected(admin_connection):
    assert admin_connection.current_user().username == "admin"
    assert admin_connection.default_project == "default"


def test_connection_logout(connection):
    connection.logout()
    assert connection.current_user() is None


def test_add_job_error(connection):
    from seamm_datastore.util import LoginRequiredError

    connection.logout()
    with pytest.raises(LoginRequiredError):
        connection.add_job({"title": "fake job"})


def test_get_users(connection):
    users = connection.get_users()
    if len(users) != 2:
        pprint.pprint(users)
    assert len(users) == 2


def test_add_job(connection):
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

    # connection.add_job(job1_data)
    connection.add_job(
        1,
        str(path / "flowchart.flow"),
        project_names=["default"],
        path=str(path),
        title="test job",
        description="description of the job",
        submitted=parser.parse("2016-08-29T09:12:33.000000+00:00"),
        started=parser.parse("2016-08-29T09:12:34.000000+00:00"),
        finished=parser.parse("2016-08-29T09:13:34.000000+00:00"),
        status="finished",
    )

    # Retrieve job
    assert len(connection.get_jobs()) == 1
