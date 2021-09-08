"""
Unit and regression test for the seamm_datastore package.
"""

# Import package, test suite, and other packages as needed
import seamm_datastore
import pytest
import sys


@pytest.fixture()
def connection():
    db = seamm_datastore.connect(
        initialize=True, username="test_user", password="password"
    )
    return db


def test_connected(connection):
    assert connection.current_user().username == "test_user"
    assert connection.default_project == "default"

def test_get_projects(connection):
    projects = connection.get_projects()
    assert len(projects) == 1


