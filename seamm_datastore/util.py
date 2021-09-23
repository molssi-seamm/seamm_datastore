"""
Util Functions and classes
"""

import re
import os
import json

from pathlib import Path

from seamm_datastore import api

from datetime import datetime
time_format = "%Y-%m-%d %H:%M:%S %Z"


def _build_initial(session, default_project):
    """Build the initial database"""

    from seamm_datastore.database.models import Role, Group, User, Project

    # Create roles
    role_names = ["user", "group manager", "admin"]
    for role_name in role_names:
        role = Role(name=role_name)
        session.add(role)
        session.commit()

    # Create default admin group
    admin_group = Group(name="admin")
    session.add(admin_group)
    session.commit()

    # Create default admin user.
    admin_role = session.query(Role).filter_by(name="admin").one()
    admin_user = User(username="admin", password="admin", roles=[admin_role])
    admin_user.groups.append(admin_group)

    # Create a user and group with the same information as user running
    try:
        item = Path.home()
        username = item.owner()
        group_name = item.group()
    except NotImplementedError:
        # This will occur on Windows
        import pwd, os, grp
        username = pwd.getpwuid(os.getuid())[0]
        group_name = grp.getgrgid(os.getgid()[0])

    group = Group(name=group_name)

    password = "default"
    user = User(username=username, password=password, roles=[admin_role])
    user.groups.append(group)

    # Admin user needs to be part of all groups.
    admin_user.groups.append(group)

    session.add(admin_user)
    session.add(admin_role)
    session.add(admin_group)

    session.add(user)

    # Create a default project
    project = Project(name=default_project, owner=user, group = group)
    session.add(project)
    session.commit()

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
        job_data["finished"] = datetime.strptime(
            job_data_json["end time"], time_format
        )

    if "start time" in job_data_json:
        job_data["started"] = datetime.strptime(
            job_data_json["start time"], time_format
        )

    return job_data


class LoginRequiredError(Exception):
    def __init__(self, message=None):
        if not message:
            self.message = "This action requires a user to be logged in."
        super().__init__(self.message)
