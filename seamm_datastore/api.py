"""
Functions which take a session and add or retrieve data to the db
"""
import os
import glob

from seamm_datastore.util import parse_flowchart


def _build_query(filter, obj):
    q = []
    for key, value in filter.items():
        q.append(getattr(obj, key).in_(value))
    return q


def get_projects(_=None, as_json=False, filter=None):
    from seamm_datastore.database.models import Project

    if not filter:
        projects = Project.query.filter(Project.authorized("read")).all()
    else:
        # Build a query
        b = _build_query(filter, Project)
        # Pass the query. Use unpacking operator to unpack generator.
        projects = Project.query.filter(
            Project.authorized("read"), *(a for a in b)
        ).all()

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
    as_json=False,
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
        flowchart = Flowchart.query.filter_by(
            sha256_strict=flowchart_info["sha256_strict"]
        ).one_or_none()
    except KeyError:
        try:
            flowchart = Flowchart.query.filter_by(id=flowchart_info["id"]).one_or_none()
        except KeyError:
            flowchart = None

    if flowchart:
        raise ValueError(f"Flowchart already in datastore. ID: {flowchart.id}")

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
        project_names = job_data["project_names"]
    except KeyError:
        job_data["project_names"] = ["default"]
        project_names = ["default"]

    projects = [Project.query.filter_by(name=x).one_or_none() for x in project_names]
    projects = [project for project in projects if project]

    if not projects:
        raise NameError(
            "Projects listed for this job not found in database, please check your project names."
        )

    # The other permissions method in flask-authorize is harder to fake,
    # but this one works.
    for project in projects:
        if project not in Project.query.filter(Project.authorized("update")).all():
            raise RuntimeError(
                f"You are not authorized to add jobs to {project} project."
            )

    try:
        job = Job.query.filter_by(id=job_data["id"]).one_or_none()
    except KeyError:
        job = None

    if job:
        raise ValueError(f"Job with ID {job.id} already found in the database")

    # Handle the flowchart - we'll only want to add it if we're adding the job.
    flowchart_filename = glob.glob(os.path.join(job_data["path"], "*.flow"))
    if len(flowchart_filename) != 1:
        raise ValueError(
            f"Invalid number of flowcharts found for a project: {len(flowchart_filename)}. There should be one flowchart per job."
        )
    fl_data, fl = parse_flowchart(flowchart_filename[0])
    fl_data["json"] = fl

    try:
        flowchart = add_flowchart(session, fl_data)
    except ValueError as e:
        from seamm_datastore.database.models import Flowchart

        id = int(e.args[0].split(":")[1])
        flowchart = Flowchart.query.filter_by(id=id).one()

    job_data["projects"] = projects
    job_data["flowchart"] = flowchart
    del job_data["project_names"]

    new_job = Job(**job_data)

    session.add(new_job)
    session.commit()

    if as_json:
        new_job = JobSchema().dump(new_job)

    return new_job


def get_jobs(_=None, as_json=False, limit=None):
    from seamm_datastore.database.models import Job

    jobs = Job.query.filter(Job.authorized("read"))

    if limit:
        jobs = jobs.limit(limit)
    else:
        jobs = jobs.all()

    if as_json:
        from seamm_datastore.database.schema import JobSchema

        jobs = JobSchema(many=True).dump(jobs)

    return jobs


def get_flowcharts(_=None, as_json=False):
    from seamm_datastore.database.models import Flowchart

    flowcharts = Flowchart.query.filter(Flowchart.authorized("read")).all()

    if as_json:
        from seamm_datastore.database.schema import FlowchartSchema

        flowcharts = FlowchartSchema(many=True).dump(flowcharts)

    return flowcharts


def get_groups(_=None, as_json=False):
    from seamm_datastore.database.models import Group

    groups = Group.query.all()

    if as_json:
        from seamm_datastore.database.schema import GroupSchema

        groups = GroupSchema(many=True).dump(groups)

    return groups


def get_users(_=None, as_json=False):
    from seamm_datastore.database.models import User

    users = User.query.all()

    if as_json:
        from seamm_datastore.database.schema import UserSchema

        users = UserSchema(many=True).dump(users)

    return users
