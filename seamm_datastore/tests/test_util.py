"""
Tests for build module
"""

import os

import seamm_datastore.util


def test_parse_flowchart_v2():
    this_file = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(this_file, "..", "data", "sample_flowchart_v2.flow")

    metadata, text = seamm_datastore.util.parse_flowchart(filepath)

    assert metadata["flowchart_version"] == 2.0
    assert (
        metadata["sha256_strict"]
        == "79d580b78559fe137872bcffe24aa7455e6c66fe260cf63e5edd3b3a1464e9c6"
    )

    assert text
