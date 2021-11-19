"""
Unit tests for projects in the seamm_datastore package.
"""
import pprint

import pytest


@pytest.fixture(scope="function")
def many(connection):
    """Create a connection with many projects."""
    user = connection.current_user().username
    for i in range(1, 100):
        name = f"project {i}"
        path = f"pdir_{i}"
        connection.add_project(name, owner=user, group="staff", path=path)

    return connection


def test_get_(connection):
    projects = connection.get_projects()
    if len(projects) != 1:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 1


def test_get_nologin(connection_nologin):
    projects = connection_nologin.get_projects()
    if len(projects) != 0:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 0


def test_add_many(connection):
    user = connection.current_user().username
    correct = ["default"]
    for i in range(1, 10):
        name = f"project {i}"
        path = f"pdir_{i}"
        connection.add_project(name, owner=user, group="staff", path=path)
        correct.append(name)
    projects = connection.list_projects()
    if len(projects) != 10 or projects != correct:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 10
    assert projects == correct


def test_many(many):
    projects = many.list_projects()
    if len(projects) != 100:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 100


def test_limit(many):
    projects = many.list_projects(limit=10)
    if len(projects) != 10:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 10


def test_offset(many):
    correct = ["project 1", "project 2", "project 3"]
    projects = many.list_projects(limit=3, offset=1)
    if len(projects) != 3 or projects != correct:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 3
    assert projects == correct


def test_count(many):
    count = many.list_projects(count=True)
    assert count == 100
