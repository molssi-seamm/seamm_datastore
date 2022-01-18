"""
Unit tests for projects in the seamm_datastore package.
"""
import pprint

import pytest

from seamm_datastore import session_scope


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

def test_add_project(tester):
    with session_scope(tester.Session) as sess:
        from seamm_datastore.api import add_project

        project = add_project(sess, name="test_name", path="test_path", owner="tester")

        assert project.owner == tester.current_user()


"""
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
"""
