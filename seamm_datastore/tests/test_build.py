"""
Tests for building/importing datastore
"""

import os


def test_build(connection):

    loc = os.path.abspath(os.path.dirname(__file__))
    added_jobs, added_projects = connection.import_datastore(
        os.path.join(loc, "..", "data", "Projects")
    )

    assert len(added_jobs) == 2
    assert len(added_projects) == 1, added_projects
