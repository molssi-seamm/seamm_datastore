"""
Functions which take a session and add or retrieve data to the db
"""


def get_projects(session, as_json=False):
    from seamm_datastore.database.models import Project

    projects = Project.query.filter(Project.authorized("read")).all()

    if as_json:
        from seamm_datastore.database.schema import ProjectSchema

        projects = ProjectSchema(many=True).dump(projects)

    return projects


def add_project(session, project_data):
    """
    Add a project to the database.

    Parameters
    ----------
    session : sqlalchemy session
    project_data : dict
    owner : User model
    """
    from seamm_datastore.database.models import Project

    project = Project.query.filter_by(name=project_data["name"]).one_or_none()

    if project:
        raise ValueError(f"User {user} already found in the database")

    new_project = Project(name=project_data["name"])

    session.add(new_project)
    session.commit()

    return new_project


def add_user(
        session,
        username,
        password,
        first_name=None,
        last_name=None,
        email=None,
        roles=None,
        groups=None,
):
    if roles is None:
        roles = ["user"]

    if groups is None:
        groups = ["staff"]

    # Verify username and password
    # Check if user exists
    from seamm_datastore.database.models import User

    user = User.query.filter_by(username=username).one_or_none()

    if user:
        raise ValueError(f"User {user} already found in the database")

    new_user = User(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
        roles=roles,
        groups=groups,
    )

    session.add(new_user)
    session.commit()

    return new_user


def add_flowchart(session, flowchart_info):
    from seamm_datastore.database.models import Flowchart

    new_flowchart = Flowchart(**flowchart_info)

    session.add(new_flowchart)
    session.commit()

    return new_flowchart


def add_job(session, job_data):
    """Add a job to the datastore.

    This method requires a user to be logged in and to have appropriate permissions
    for the project.
    """
    from seamm_datastore.database.models import Job, Project

    try:
        project_name = job_data["project_name"]
    except KeyError:
        project_name = "default"

    project = Project.query.filter_by(name=project_name).one_or_none()

    if not project:
        raise NameError(
            f"Project {project_name} not found in database, please check your project name."
        )

    # The other permissions method in flask-authorize is harder to fake,
    # but this one works.
    if project not in Project.query.filter(Project.authorized("update")).all():
        raise RuntimeError("You are not authorized to add jobs to this project.")

    new_job = Job(**job_data)

    session.add(new_job)
    session.commit()

    return new_job
