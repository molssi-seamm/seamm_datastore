"""
Util Functions and classes
"""

import json
import os
import re
from datetime import datetime
from dateutil import parser

def parse_flowchart(path):
    """
    Function for parsing information from flowchart

    Parameters
    ----------
    path: str
        The path to the flowchart.

    Returns
    -------
    metadata: dict
        A json containing flowchart information to be added to the database.
    """

    with open(path) as f:
        f.readline()
        version_info = " " + f.readline().split()[-1]
        text = f.read()

    if " 1." in version_info:
        metadata_pattern = None
        flowchart_pattern = re.compile("{.+}", re.DOTALL)
    elif " 2." in version_info:
        # Flowchart is version 2.
        metadata_pattern = re.compile("#metadata\n({.+?})\n#", re.DOTALL)
        flowchart_pattern = re.compile("#flowchart\n({.+})\n?#", re.DOTALL)
    else:
        # TODO Maybe raise custom exception. SEAMM Flowchart version error
        # Value Error for now
        raise ValueError

    # Handle the metadata
    if metadata_pattern:
        metadata = json.loads(metadata_pattern.findall(text)[0])
    else:
        metadata = {}

    # metadata as a json, flowchart (json) as text.
    metadata["flowchart_version"] = float(version_info)
    flowchart = flowchart_pattern.findall(text)[0]

    return metadata, flowchart


def parse_job_data(path):
    """Parse job_data.json at path"""

    directory = os.path.dirname(path)

    with open(path) as f:
        job_data_json = json.load(f)
    job_data = {
        "path": directory,
        "title": str(
            job_data_json["title"]
            if job_data_json["title"]
            else os.path.basename(os.path.dirname(path))
        ),
        "project_names": job_data_json["projects"],
        "status": job_data_json["state"],
        "id": job_data_json["job id"],
    }

    if "end time" in job_data_json:
        job_data["finished"] = parser.parse(job_data_json["end time"])

    if "start time" in job_data_json:
        job_data["started"] = parser.parse(job_data_json["start time"])

    return job_data


class LoginRequiredError(Exception):
    def __init__(self, message=None):
        if not message:
            self.message = "This action requires a user to be logged in."
        super().__init__(self.message)
