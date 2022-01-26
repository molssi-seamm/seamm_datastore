"""
API Tests
"""

import pytest

from pathlib import Path

import seamm_datastore

import pprint
import pytest

from dateutil import parser

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
    seamm_datastore.api.add_job(connection.Session,
        job_id=1,
        flowchart_filename=str(path / "flowchart.flow"),
        project_names=["default"],
        path=str(path),
        title="test job",
        description="description of the job",
        submitted=parser.parse("2016-08-29T09:12:33.000000+00:00"),
        started=parser.parse("2016-08-29T09:12:34.000000+00:00"),
        finished=parser.parse("2016-08-29T09:13:34.000000+00:00"),
        status="finished",
    )