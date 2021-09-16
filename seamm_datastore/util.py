"""
Util Functions and classes
"""

import re
import json

from pathlib import Path

from seamm_datastore import api


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
    group = Group(name="admin")
    session.add(group)
    session.commit()

    # Create default admin user.
    admin_role = session.query(Role).filter_by(name="admin").one()
    user = User(username="admin", password="admin", roles=[admin_role])
    user.groups.append(group)
    session.add(user)
    session.add(admin_role)
    session.add(group)

    # Create a user with the same username as user running
    item = Path.home()
    username = item.owner()
    password = "default"
    user = User(username=username, password=password, roles=[admin_role])
    user.groups.append(group)
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


class LoginRequiredError(Exception):
    def __init__(self, message=None):
        if not message:
            self.message = "This action requires a user to be logged in."
        super().__init__(self.message)
