"""
API Tests
"""

import pytest


@pytest.mark.parametrize(
    "resource, description, title, offset, limit, sort, order, num_records, first_id",
    [
        (
            "job",
            None,
            None,
            None,
            None,
            "id",
            "asc",
            2,
            92,
        ),  # Test retrieving all jobs default sort
        (
            "job",
            None,
            None,
            None,
            None,
            "id",
            "desc",
            2,
            93,
        ),  # Test retrieving all jobs, descending sort
        (
            "job",
            None,
            None,
            None,
            None,
            "last_update",
            "desc",
            2,
            93,
        ),  # Test retrieving all jobs, descending sort by last update time.
        (
            "project",
            None,
            None,
            None,
            None,
            "id",
            "asc",
            2,
            1,
        ),  # Test retrieving all projects
        (
            "flowchart",
            None,
            None,
            None,
            None,
            "id",
            "asc",
            1,
            1,
        ),  # Test retrieving all flowcharts
        ("job", None, None, 1, None, "id", "asc", 1, 93),  # Get jobs with offset
        ("job", None, None, None, 1, "id", "asc", 1, 92),  # Get jobs with offset
        ("job", None, "Test", None, None, "id", "asc", 1, 92),
    ],
)
def test_get_queries(
    filled_db,
    resource,
    description,
    title,
    offset,
    limit,
    sort,
    order,
    num_records,
    first_id,
):
    from seamm_datastore.database.models import Job, Project, Flowchart

    resource_map = {"job": Job, "flowchart": Flowchart, "project": Project}

    resource = resource_map[resource]

    records = resource.get(
        description=description,
        title=title,
        offset=offset,
        limit=limit,
        sort_by=sort,
        order=order,
    )

    assert len(records) == num_records

    # Since the test relies on database that is built for testing,
    # we don't know for sure which one is added first. Confirm with
    # times. Not the ideal way :)
    if sort == "last_update":
        if order == "desc":
            assert records[0].last_update >= records[1].last_update
        else:
            assert records[0].last_update <= records[1].last_update
    else:
        assert records[0].id == first_id

    assert isinstance(records[0], resource)


def test_job_update_error(filled_db):
    from seamm_datastore.database.models import Job

    with pytest.raises(ValueError):
        Job.update(1, description="This is a new description.")


def test_job_update(filled_db):
    from seamm_datastore.database.models import Job

    job = Job.update(92, description="This is a new description.")

    assert job.description == "This is a new description."
