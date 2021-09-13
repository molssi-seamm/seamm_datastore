"""
Unit and regression test for the seamm_datastore package.
"""

# Import package, test suite, and other packages as needed
import pytest

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
        connection.add_job("fake job")


