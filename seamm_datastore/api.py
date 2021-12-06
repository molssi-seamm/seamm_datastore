"""
Functions which take a session and add or retrieve data to the db
"""
import datetime
import pprint  # noqa: F401

from seamm_datastore.util import parse_flowchart


def _build_query(filter, obj):
    q = []
    for key, value in filter.items():
        q.append(getattr(obj, key).in_(value))
    return q


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


def add_group(
    session,
    name,
    as_json=False,
    current_user=None,
):
    """
    Add a project to the database.

    Parameters
    ----------
    session : sqlalchemy.Session
        The session used to access the database.
    name : str
        The name of the project, used for display and directory name.
    as_json : bool = False
        If True, return the json description of the project; otherwise, the project id.
    current_user : str or User = None
        The user currently logged in. Not used.

    Returns
    -------
    json or Group
        The json describing the new project, or the Group object, deoending on
        "as_json".
    """
    from seamm_datastore.database.models import Group
    from seamm_datastore.database.schema import GroupSchema

    # Check that the group doesn't already exist.
    group = Group.query.filter_by(name=name).one_or_none()
    if group is not None:
        raise ValueError(f"Group '{group}' already exists.")

    group = Group(name=name)
    session.add(group)
    session.commit()

    # Return the json or id as requested.
    if as_json:
        group_schema = GroupSchema()
        return group_schema.dump(group)
    else:
        return group


def add_job(
    session,
    job_id,
    flowchart_filename,
    project_names=["default"],
    path=None,
    title="",
    description="",
    submitted=datetime.datetime.now(datetime.timezone.utc),
    started=None,
    finished=None,
    status="submitted",
    as_json=False,
    current_user=None,
):
    """Submit a job to the datastore.

    This method requires a user to be logged in and to have appropriate permissions
    for the project.

    Parameters
    ----------
    session : sqlalchemy.Session
        The session used to access the database.
    job_id : int
        The id of the job, an integer > 0.
    flowchart_filename : str or pathlib.Path
        The path to the file containing the flowchart.
    project_names : [str]
        A list of projects that the flowchart belongs to.
    path : str
        The directory path for the job.
    title : str = ""
        The title of the job, used for display.
    description : str = ""
        A longer, textual description of the job.
    submitted : datetime.datetime = now()
        When the job was submitted as a datetime object. Defaults to now in UTC.
    started : datetime.datetime = None
        When the job was started, if it was. Preferably in UTC.
    finished : datetime.datetime = None
        When the job finished, if it has. Preferably in UTC.
    status : str = "submitted"
        The status of the job: "submitted", "running", "finished", "error", etc.
    as_json : bool = False
        If true return the job data asjson, otehrwise return the Job object.
    current_user : str or User = None
        The user currently logged in. Not used.

    Returns
    -------
    json or Job
        The json of the job data, or the Job object, depending on "as_json".
    """
    from seamm_datastore.database.models import Job, Project
    from seamm_datastore.database.schema import JobSchema

    # Check if this job already exists
    try:
        job = Job.query.filter_by(id=job_id).one_or_none()
    except KeyError:
        job = None
    if job:
        raise ValueError(f"Job with ID {job_id} already found in the database")

    # Get the ids for the projects
    projects = [Project.query.filter_by(name=x).one_or_none() for x in project_names]
    projects = [project for project in projects if project]

    if not projects:
        tmp = "', '".join(project_names)
        raise NameError(
            "Projects listed for this job not found in database."
            f"\nPlease check your project names: '{tmp}'"
        )

    # Check the permissions of the projects to see if we can add a job to them
    allowed_projects = Project.query.filter(Project.authorized("update")).all()
    for project in projects:
        # if project not in Project.query.filter(Project.authorized("update")).all():
        if project not in allowed_projects:
            raise RuntimeError(
                f"You are not authorized to add jobs to {project} project."
            )

    # Handle the flowchart - we'll only want to add it if we're adding the job.
    fl_data, fl = parse_flowchart(flowchart_filename)
    fl_data["json"] = fl

    try:
        flowchart = add_flowchart(session, fl_data)
    except ValueError as e:
        from seamm_datastore.database.models import Flowchart

        id = int(e.args[0].split(":")[1])
        flowchart = Flowchart.query.filter_by(id=id).one()

    # Now add the job and update the database
    new_job = Job(
        id=job_id,
        title=title,
        description=description,
        path=path,
        flowchart=flowchart,
        projects=projects,
        status=status,
        submitted=submitted,
        started=started,
        finished=finished,
    )
    session.add(new_job)
    session.commit()

    # Return the job as json or an object.
    if as_json:
        return JobSchema().dump(new_job)
    else:
        return new_job


def add_project(
    session,
    name,
    description="",
    path=None,
    owner=None,
    group=None,
    as_json=False,
    current_user=None,
):
    """
    Add a project to the database.

    Parameters
    ----------
    session : sqlalchemy.Session
        The session used to access the database.
    name : str
        The name of the project, used for display and directory name.
    description : str
        A textual description of the project.
    path : str = None
        The path on disk to the project files.
    owner : str or User = None
        An optional user to own the project. Defaults to the currently logged in user.
    group : str or Group = None
        The group for the project. Defaults to user's primary group.
    as_json : bool = False
        If True, return the json description of the project; otherwise, the project id.
    current_user : str or User = None
        The user currently logged in.

    Returns
    -------
    json or Project
        The json describing the new project, or the Project object, deoending on
        "as_json".
    """
    from seamm_datastore.database.models import Project, User, Group
    from seamm_datastore.database.schema import ProjectSchema, UserSchema

    # Check that the project doesn't already exist.
    project = Project.query.filter_by(name=name).one_or_none()
    if project is not None:
        raise ValueError(f"Project {project} already found in the database")

    # Sort out the user and get as a User object.
    if owner is None:
        if current_user is None:
            raise ValueError("The owner is required for adding a project.")
        else:
            owner = current_user
    if isinstance(owner, str):
        owner_id = User.query.filter_by(username=owner).one()
        owner = owner_id

    # Get the group as a Group object. The default is the user's first group.
    if group is None:
        owner_info = UserSchema().dump(owner)
        group = Group.query.filter_by(id=owner_info["groups"][0]).one()
    elif isinstance(group, str):
        group_id = Group.query.filter_by(name=group).one()
        group = group_id

    # Create the project and sotr in the database
    project = Project(
        name=name, description=description, path=path, owner=owner, group=group
    )
    session.add(project)
    session.commit()

    # Return the json or id as requested.
    if as_json:
        project_schema = ProjectSchema()
        return project_schema.dump(project)
    else:
        return project


def add_user(
    session,
    username,
    password,
    first_name=None,
    last_name=None,
    email=None,
    roles=["user"],
    groups=["staff"],
    as_json=False,
    current_user=None,
):
    """
    Add a new user to the database.

    Parameters
    ----------
    session : sqlalchemy.Session
        The session used to access the database.
    username : str
        The username that identifies the user.
    password : str
        The secret password for the user.
    first_name : str = None
        The user's first (given) name.
    last_name : str = None
        The user's last (family) name.
    email : str = None
        The user's principal email address.
    roles : [str] = ["user"]
        A list of roles for the user. Defaults to just "user".
    groups : [str] = ["staff"]
        A list of groups that the user belongs to. Defaults to "staff".
    as_json : bool = False
        If True, return the json description of the user; otherwise, the user id.
    current_user : str or User = None
        The user currently logged in. Not used.
    """
    from seamm_datastore.database.models import Group, Role, User
    from seamm_datastore.database.schema import UserSchema

    # Check if the user already exists.
    user = User.query.filter_by(username=username).one_or_none()
    if user:
        raise ValueError(f"User {user} already found in the database")

    # Create the new user and store in the database
    new_user = User(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    for role_name in roles:
        role = Role.query.filter_by(name=role_name).one()
        new_user.roles.append(role)
    for group_name in groups:
        group = Group.query.filter_by(name=group_name).one()
        new_user.groups.append(group)
    session.add(new_user)
    session.commit()

    # Return the json or user, as requested.
    if as_json:
        return UserSchema().dump(new_user)
    else:
        return new_user


def finish_job(
    session,
    job_id,
    finish_time,
    status="finished",
    as_json=False,
    current_user=None,
):
    """Set the status and time that the job finished.

    Parameters
    ----------
    session : session object
        The SQLAlchemy session
    job_id : int
        The ID of the job, eg. 209
    finish_time : datetime.datetime
        The UTC time when the job finished.
    status : str
        The status, such as "error" or the default, "finished"
    as_json : bool = False
        Ignored
    current_user : str or User = None
        Ignored

    Returns
    -------
    bool
        True if the finish time was successfully set, False otherwise.
    """
    from seamm_datastore.database.models import Job

    job = Job.query.filter_by(id=job_id).one_or_none()
    if job is None:
        return False
    else:
        job.finished = finish_time
        job.status = status
        session.commit()
        return True


def get_flowcharts(_=None, as_json=False, current_user=None):
    from seamm_datastore.database.models import Flowchart

    flowcharts = Flowchart.query.filter(Flowchart.authorized("read")).all()

    if as_json:
        from seamm_datastore.database.schema import FlowchartSchema

        flowcharts = FlowchartSchema(many=True).dump(flowcharts)

    return flowcharts


def get_groups(_=None, as_json=False, current_user=None):
    from seamm_datastore.database.models import Group

    groups = Group.query.all()

    if as_json:
        from seamm_datastore.database.schema import GroupSchema

        groups = GroupSchema(many=True).dump(groups)

    return groups


def get_job(session, id, as_json=False):

    from seamm_datastore.database.models import Job, Project
    from .util import NotAuthorizedError

    authorized_job = Job.query.filter(Job.authorized("read"), Job.id == id)
    project_job = Project.query.with_entities(Job).filter(
        Project.authorized("read"), Job.id == id
    )

    project_job = Job.query.filter(
        Job.projects.any(Project.authorized("read")), Job.id == id
    )

    # Do we get the job?
    job = authorized_job.union(project_job).one_or_none()

    if job is None and Job.query.get(id):
        raise NotAuthorizedError

    if as_json:
        from seamm_datastore.database.schema import JobSchema

        job = JobSchema().dump(job)

    return job


def get_jobs(_=None, as_json=False, limit=None, offset=None, count=False, status=None):

    from seamm_datastore.database.models import Job, Project

    # Get the jobs where the user has read permission
    if status is None:
        authorized_jobs = Job.query.filter(Job.authorized("read"))
    else:
        authorized_jobs = Job.query.filter(Job.authorized("read"), Job.status == status)

    # Get jobs from projects where user has read permission
    if status is None:
        project_jobs = Job.query.filter(Job.projects.any(Project.authorized("read")))
    else:
        project_jobs = Job.query.filter(
            Job.projects.any(Project.authorized("read")), Job.status == status
        )

    # Find union of these queries
    jobs = authorized_jobs.union(project_jobs)

    # Continue building
    if limit is not None:
        jobs = jobs.limit(limit)
    if offset is not None:
        jobs = jobs.offset(offset)

    if count is True:
        jobs = jobs.count()
    else:
        jobs = jobs.all()

        if as_json:
            from seamm_datastore.database.schema import JobSchema

            jobs = JobSchema(many=True).dump(jobs)

    return jobs


def get_projects(
    session=None,
    action="read",
    filter=None,
    limit=None,
    offset=None,
    count=False,
    as_json=False,
    current_user=None,
):
    """Get the projects in the datastore.

    Parameters
    ----------
    session : Session object = None
        The SQLAlchemy session or equivalent. Not used.
    action : str = "read"
        Whether to get readable ("read") of writeable ("update") projects.
    filter : dict = None
        A dictionary of query conditions for filtering the results.
    limit : int = None
        The maximum number of records to return.
    offset : int = None
        Return the records starting at offset (0-based). Used with limit to page through
        records.
    count : bool = False
        If true, return the number of records returned by the query.
    as_json : bool = False
        If true return json for an array of dictionaries describing the projects.
        If false, return just the list of project names.
    current_user : str or User = None
        The user currently logged in. Not used.

    Returns
    -------
    int, [str], or json
        The integer count of records if "count" is True.
        A list of project names if "as_json" is False.
        And array of dictionaries as json if "as_json" is True.
    """
    from seamm_datastore.database.models import Project

    if filter is None:
        query = Project.query.filter(Project.authorized(action))
    else:
        # Build a query
        b = _build_query(filter, Project)
        # Pass the query. Use unpacking operator to unpack generator.
        projects = Project.query.filter(
            Project.authorized(action), *(a for a in b)
        ).all()

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    if count:
        result = query.count()
    else:
        projects = query.all()
        if as_json:
            from seamm_datastore.database.schema import ProjectSchema

            result = ProjectSchema(many=True).dump(projects)
        else:
            result = [p.name for p in projects]

    return result


def get_users(_=None, as_json=False, current_user=None):
    from seamm_datastore.database.models import User

    users = User.query.all()

    if as_json:
        from seamm_datastore.database.schema import UserSchema

        users = UserSchema(many=True).dump(users)

    return users


def list_projects(
    _=None,
    action="read",
    filter=None,
    limit=None,
    offset=None,
    count=False,
    as_json=False,
    current_user=None,
):
    """Get a list of projects in the datastore.

    Parameters
    ----------
    session : Session object = None
        The SQLAlchemy session or equivalent. Not used.
    action : str = "read"
        Whether to get readable ("read") of writeable ("update") projects.
    filter : dict = None
        A dictionary of query conditions for filtering the results.
    limit : int = None
        The maximum number of records to return.
    offset : int = None
        Return the records starting at offset (0-based). Used with limit to page through
        records.
    count : bool = False
        If true, return the number of records returned by the query.
    as_json : bool = False
        Ignored
    current_user : str or User = None
        Ignored

    Returns
    -------
    int, [str]
        The integer count of records if "count" is True, otherwise a list of project
        names.
    """
    return get_projects(
        None,
        action=action,
        filter=filter,
        limit=limit,
        offset=offset,
        count=count,
        as_json=None,
    )
