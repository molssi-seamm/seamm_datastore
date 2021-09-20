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


def add_project(session, project_data, as_json=False):
    """
    Add a project to the database.

    Parameters
    ----------
    session : sqlalchemy session
    project_data : dict
    as_json : bool
    """
    from seamm_datastore.database.models import Project, User, Group
    from seamm_datastore.database.schema import ProjectSchema

    project = Project.query.filter_by(name=project_data["name"]).one_or_none()

    if project:
        raise ValueError(f"Project {project} already found in the database")

    if isinstance(project_data["owner"], str):
        user = User.query.filter_by(username=project_data["owner"]).one()
        project_data["owner"] = user

    if isinstance(project_data["group"], str):
        group = Group.query.filter_by(name=project_data["group"]).one()
        project_data["group"] = group

    print(f"Owner is {user.username}")
    new_project = Project(**project_data)

    session.add(new_project)
    session.commit()

    if as_json:
        project_schema = ProjectSchema()
        new_project = project_schema.dump(new_project)

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
        as_json=False
):
    if roles is None:
        roles = ["user"]

    if groups is None:
        groups = ["staff"]

    # Verify username and password
    # Check if user exists
    from seamm_datastore.database.models import User
    from seamm_datastore.database.schema import UserSchema

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

    if as_json:
        new_user = UserSchema().dump(new_user)

    return new_user


def add_flowchart(session, flowchart_info):
    from seamm_datastore.database.models import Flowchart

    try:
        flowhcart = Flowchart.query.filter_by(flowchart_info["id"]).one_or_none()
    except KeyError:
        flowchart = None

    if flowhcart:
        raise ValueError(f"Flowchart with ID {flowchart.id} already in datastore.")

    new_flowchart = Flowchart(**flowchart_info)

    session.add(new_flowchart)
    session.commit()

    return new_flowchart


def add_job(session, job_data, as_json=False):
    """Add a job to the datastore.

    This method requires a user to be logged in and to have appropriate permissions
    for the project.
    """
    from seamm_datastore.database.models import Job, Project
    from seamm_datastore.database.schema import JobSchema

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

    try:
        job = Job.query.filter_by(id=job_data["id"]).one_or_none()
    except KeyError:
        job = None

    if job:
        raise ValueError(f"Job with ID {job.id} already found in the database")

    new_job = Job(**job_data)

    session.add(new_job)
    session.commit()

    if as_json:
        new_job = JobSchema().dump(new_job)

    return new_job


def get_jobs(session, as_json=False):
    from seamm_datastore.database.models import Job

    jobs = Job.query.filter(Job.authorized("read")).all()

    if as_json:
        from seamm_datastore.database.schema import JobSchema

        jobs = JobSchema(many=True).dump(jobs)

    return jobs


def get_groups(session, as_json=False):
    from seamm_datastore.database.models import Group

    groups = Group.query.all()

    if as_json:
        from seamm_datastore.database.schema import GroupSchema

        groups = GroupSchema(many=True).dump(groups)

    return groups

def get_users(session, as_json=False):
    from seamm_datastore.database.models import User

    users = User.query.all()

    if as_json:
        from seamm_datastore.database.schema import UserSchema

        users = UserSchema(many=True).dump(users)

    return users



