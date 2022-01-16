"""
API Tests
"""

import pytest

#from seamm_datastore.database.models import Job, Flowchart
#rom seamm_datastore.connect import session_scope


@pytest.fixture(scope="function")
def many(admin_connection):
    """Create a connection with many projects."""
    conn = admin_connection

    from seamm_datastore.connect import session_scope

    with session_scope(conn.Session) as sess:
        from seamm_datastore.database.models import Job
        for i in range(1, 101):
            name = f"project {i}"
            path = f"pdir_{i}"
            job = Job(title=name, path=path)
            sess.add(job)
        sess.commit()
            
    return conn

@pytest.mark.parametrize("parameters, expected, first_id", [
    ({"limit":5}, 5, 1),
    ({}, 100, 1),
    ({"limit":5, "offset": 10}, 5, 11),
    ({"offset": 50}, 50, 51)
])
def test_get_jobs(many, parameters, expected, first_id):
    jobs = many.get_jobs(**parameters)

    assert len(jobs) == expected
    assert jobs[0]["id"] == first_id