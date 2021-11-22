"""
Unit tests for projects in the seamm_datastore package.
"""
import pprint

import pytest


@pytest.fixture(scope="function")
def tester(connection_nologin):
    """Create a connection with user "tester"."""
    conn = connection_nologin
    conn.login("admin", "admin")
    conn.add_group("test")
    conn.add_user("tester", "default", groups=["test"])
    conn.logout()
    conn.login("tester", "default")

    return conn


@pytest.fixture(scope="function")
def many(tester):
    """Create a connection with many projects."""
    conn = tester
    for i in range(1, 101):
        name = f"project {i}"
        path = f"pdir_{i}"
        conn.add_project(name, owner="tester", group="test", path=path)

    return conn


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


def test_add_many(tester):
    correct = []
    for i in range(1, 11):
        name = f"project {i}"
        path = f"pdir_{i}"
        tester.add_project(name, owner="tester", group="test", path=path)
        correct.append(name)
    projects = tester.list_projects()
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
    correct = ["project 2", "project 3", "project 4"]
    projects = many.list_projects(limit=3, offset=1)
    if len(projects) != 3 or projects != correct:
        pprint.pprint(f"{projects=}")
    assert len(projects) == 3
    assert projects == correct


def test_count(many):
    count = many.list_projects(count=True)
    assert count == 100
