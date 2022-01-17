"""
API Tests
"""

import pytest

from seamm_datastore.util import NotAuthorizedError

# from seamm_datastore.database.models import Job, Flowchart
# rom seamm_datastore.connect import session_scope


@pytest.fixture(scope="function")
def many_jobs(admin_connection):
    """Create a connection with many jobs."""
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


@pytest.fixture(scope="function")
def many_flowcharts(admin_connection):
    """Create a connection with many flowcharts."""
    conn = admin_connection

    from seamm_datastore.connect import session_scope

    with session_scope(conn.Session) as sess:
        from seamm_datastore.database.models import Flowchart

        for i in range(1, 101):
            name = f"project {i}"
            path = f"pdir_{i}"
            flowchart = Flowchart(json={"Key": "value"}, path=path)
            sess.add(flowchart)
        sess.commit()
    return conn


@pytest.mark.parametrize(
    "parameters, expected, first_id",
    [
        ({"limit": 5}, 5, 1),
        ({}, 100, 1),
        ({"limit": 5, "offset": 10}, 5, 11),
        ({"offset": 50}, 50, 51),
    ],
)
def test_get_jobs(many_jobs, parameters, expected, first_id):
    jobs = many_jobs.get_jobs(**parameters)

    assert len(jobs) == expected
    assert jobs[0]["id"] == first_id


@pytest.mark.parametrize("job_id, authorized", [(1, True), (1, False)])
def test_get_job(job_id, authorized, many_jobs):

    if authorized is False:
        many_jobs.logout()
        with pytest.raises(NotAuthorizedError):
            many_jobs.get_job(job_id)
    else:
        job = many_jobs.get_job(job_id)
        assert job["id"] == 1


@pytest.mark.parametrize(
    "parameters, expected, first_id",
    [
        ({"limit": 5}, 5, 1),
        ({}, 100, 1),
        ({"limit": 5, "offset": 10}, 5, 11),
        ({"offset": 50}, 50, 51),
    ],
)
def test_get_flowcharts(many_flowcharts, parameters, expected, first_id):
    flowcharts = many_flowcharts.get_flowcharts(**parameters)

    assert len(flowcharts) == expected
    assert flowcharts[0]["id"] == first_id
    assert "flowchart_version" in flowcharts[0].keys()
