"""
Table models for SEAMM datastore SQLAlchemy database.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Table,
    Text,
    JSON,
    Float,
)
from sqlalchemy.orm import relationship

from sqlalchemy.ext.declarative import declarative_base

# Patched flask authorize
from seamm_datastore.flask_authorize_patch import (
    AccessControlPermissionsMixin,
    generate_association_table,
)

from seamm_datastore.util import NotAuthorizedError

# The default is sqlalchemy unless we have
# the dashboard installed and a db with
# a bound engine.
try:
    import sys

    assert "seamm_dashboard" in sys.modules
    from seamm_dashboard import db

    Base = db.Model
except AssertionError:
    Base = declarative_base()

#############################
#
# SQLAlchemy Models
#
#############################

# Authentication Mapping Tables for Access Control
UserProjectMixin = generate_association_table("User", "Project")
GroupProjectMixin = generate_association_table("Group", "Project")


class UserProjectAssociation(Base, UserProjectMixin):
    pass


class GroupProjectAssociation(Base, GroupProjectMixin):
    pass


user_group = Table(
    "user_group",
    Base.metadata,
    Column("user", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group", Integer, ForeignKey("groups.id"), primary_key=True),
)

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role", Integer, ForeignKey("roles.id"), primary_key=True),
)


flowchart_project = Table(
    "flowchart_project",
    Base.metadata,
    Column("flowchart", String(32), ForeignKey("flowcharts.id"), primary_key=True),
    Column("project", Integer, ForeignKey("projects.id"), primary_key=True),
)

job_project = Table(
    "job_project",
    Base.metadata,
    Column("job", Integer, ForeignKey("jobs.id"), primary_key=True),
    Column("project", Integer, ForeignKey("projects.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    added = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, default="active")

    roles = relationship("Role", secondary=user_role, back_populates="users")
    groups = relationship("Group", secondary=user_group, back_populates="users")

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def create(
        cls,
        username,
        password,
        first_name=None,
        last_name=None,
        email=None,
        roles=["user"],
        groups=None,
    ):
        """
        Create a new user to be added to the database.

        Parameters
        ----------
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
        groups : [str] = None
            A list of groups that the user belongs to.
            Defaults to the first group in the database.
        """

        # Check if the user already exists.
        user = cls.query.filter_by(username=username).one_or_none()
        if user:
            raise ValueError(f"User {user.username} already found in the database")

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

        if groups is None:
            groups = [Group.query.get(2).name]

        for group_name in groups:
            group = Group.query.filter_by(name=group_name).one()
            new_user.groups.append(group)

        return new_user


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_group, back_populates="groups")

    @classmethod
    def create(cls, name, users):
        """
        Add a project to the database.

        Parameters
        ----------
        name : str
            The name of the project, used for display and directory name.
        users : list
            A list of usernames to add to the group

        Returns
        -------
        Group
            A Group object
        """

        # Check that the group doesn't already exist.
        group = cls.query.filter_by(name=name).one_or_none()

        if group is not None:
            raise ValueError(f"Group '{group}' already exists.")

        group = Group(name=name)

        for username in users:
            user = User.query.filter_by(username=username).one_or_none()

            if user is None:
                raise ValueError("Invalid username {username} supplied.")

            group.users.append(user)

        return group


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_role, back_populates="roles")


#######################
#
# Base resource class
#
#######################


class Resource(AccessControlPermissionsMixin):
    @classmethod
    def permissions_query(cls, permission):
        self_read = cls.query.filter(cls.authorized(permission))
        self_projects = cls.query.filter(
            cls.projects.any(Project.authorized(permission))
        )
        return self_read.union(self_projects)

    @classmethod
    def get(
        cls,
        permission="read",
        description=None,
        title=None,
        offset=None,
        limit=None,
        sort_by="id",
        order="asc",
        only="all",
    ):
        """General get method for jobs, flowcharts, projects"""

        perm_query = cls.permissions_query(permission.lower())

        if order.lower() == "desc":
            perm_query = perm_query.order_by(cls.__dict__[sort_by].desc())

        if description is not None:
            # Build string
            perm_query = perm_query.filter(cls.description.contains(description))

        if title is not None:
            perm_query = perm_query.filter(cls.title.contains(title))

        if limit is not None:
            perm_query = perm_query.limit(limit)

        if offset is not None:
            perm_query = perm_query.offset(offset)

        if only != "all":
            perm_query = perm_query.values(*(cls.__dict__[x] for x in only))
            return perm_query
        else:
            return perm_query.all()

    @classmethod
    def get_by_id(cls, id, permission="read"):
        """General get method for retrieving by ID"""
        perm_query = (
            cls.permissions_query(permission.lower()).filter_by(id=id).one_or_none()
        )
        regular_query = cls.query.filter(cls.id == id).one_or_none()

        if perm_query is None and regular_query is not None:
            raise NotAuthorizedError

        return perm_query


class Flowchart(Base, Resource):
    __tablename__ = "flowcharts"

    id = Column(Integer, nullable=False, primary_key=True)
    sha256 = Column(String(75), nullable=True)
    sha256_strict = Column(String(75), nullable=True)
    flowchart_version = Column(Float, nullable=True, unique=False)
    doi = Column(Text, nullable=True)
    conceptdoi = Column(Text, nullable=True)
    title = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    creators = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    json = Column(JSON, nullable=False)
    flowchart_metadata = Column(JSON, nullable=True)

    jobs = relationship("Job", back_populates="flowchart", lazy=True)
    projects = relationship(
        "Project", secondary=flowchart_project, back_populates="flowcharts"
    )

    @classmethod
    def create(cls, **flowchart_info):
        try:
            flowchart = cls.query.filter_by(
                sha256_strict=flowchart_info["sha256_strict"]
            ).one_or_none()
        except KeyError:
            try:
                flowchart = Flowchart.query.filter_by(
                    id=flowchart_info["id"]
                ).one_or_none()
            except KeyError:
                flowchart = None

        if flowchart:
            raise ValueError(f"Flowchart already in datastore. ID: {flowchart.id}")

        # These are basically all of the columns in a flowchart
        column_metadata = [
            "title",
            "keywords",
            "creators",
            "doi",
            "conceptdoi",
            "sha256",
            "sha256_strict",
            "json",
            "description",
            "flowchart_version",
            "flowchart_metadata",
        ]

        if "path" in flowchart_info.keys():
            del flowchart_info["path"]

        flowchart_info["flowchart_metadata"] = {}

        # This will remove any keyword in the metadata that is not explicitly
        # stored and save it in the
        # 'flowchart_metadata' column
        to_remove = []
        for k, v in flowchart_info.items():
            if k not in column_metadata:
                flowchart_info["flowchart_metadata"][k] = v
                to_remove.append(k)

        # delete keys that are in flowchart metatdata column from flowchart_info
        for k in to_remove:
            del flowchart_info[k]

        new_flowchart = Flowchart(**flowchart_info)

        return new_flowchart

    @classmethod
    def create_from_file(cls, path):
        metadata, flowchart = cls.parse_flowchart_file(path)

        metadata["json"] = flowchart
        if "name" in metadata.keys():
            metadata["title"] = metadata["name"]
            del metadata["name"]

        return cls.create(**metadata)

    @staticmethod
    def parse_flowchart_file(path):
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

        import re
        import json

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


class Job(Base, Resource):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    flowchart_id = Column(String(32), ForeignKey("flowcharts.id"))
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    path = Column(String, unique=True)
    submitted = Column(DateTime, nullable=False, default=datetime.utcnow)
    started = Column(DateTime, nullable=True)
    finished = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="imported")
    last_update = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    parameters = Column(JSON, nullable=True)

    flowchart = relationship("Flowchart", back_populates="jobs")
    projects = relationship("Project", secondary=job_project, back_populates="jobs")

    def __repr__(self):
        return f"Job(path={self.path}, flowchart_id={self.flowchart}, submitted={self.submitted})"  # noqa: E501

    @staticmethod
    def parse_job_data(path):
        """Parse job_data.json at path"""

        import os
        import json

        from dateutil import parser

        from datetime import timezone

        directory = os.path.dirname(path)

        # Assumes first line is a comment
        with open(path) as f:
            f.readline()
            job_data_json = json.loads(f.read())

        directory = job_data_json["working directory"]
        job_data = {
            "path": directory,
            "title": str(
                job_data_json["title"]
                if job_data_json["title"]
                else os.path.basename(directory)
            ),
            "project_names": job_data_json["projects"],
            "status": job_data_json["state"],
            "id": job_data_json["job id"],
        }

        if "end time" in job_data_json:
            try:
                job_data["finished"] = datetime.fromisoformat(job_data_json["end time"])
            except Exception:
                job_data["finished"] = parser.parse(
                    job_data_json["end time"]
                ).astimezone(timezone.utc)

        if "start time" in job_data_json:
            try:
                job_data["started"] = datetime.fromisoformat(
                    job_data_json["start time"]
                )
            except Exception:
                job_data["started"] = parser.parse(
                    job_data_json["start time"]
                ).astimezone(timezone.utc)

        if "submitted time" in job_data_json:
            job_data["submitted"] = datetime.fromisoformat(
                job_data_json["submitted time"]
            )
        elif "started" in job_data:
            job_data["submitted"] = job_data["started"]

        return job_data

    @classmethod
    def create(
        cls,
        id,
        flowchart_filename,
        project_names=["default"],
        path=None,
        title="",
        description="",
        submitted=None,
        started=None,
        finished=None,
        parameters=None,
        status="submitted",
    ):
        """Create a new job to add to the datastore.

        This method requires a user to be logged in and to have appropriate permissions
        for the project.

        Parameters
        ----------
        id : int
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
        parameters : dict
            The command-line parameters for the job.
        status : str = "submitted"
            The status of the job: "submitted", "running", "finished", "error", etc.

        Returns
        -------
        json or Job
            The json of the job data, or the Job object, depending on "as_json".
        """

        # Check if this job already exists
        try:
            job = Job.query.filter(Job.id == id).one_or_none()
        except KeyError:
            job = None
        if job:
            raise ValueError(f"Job with ID {id} already found in the database")

        if submitted is None:
            submitted = datetime.utcnow()

        # Get the ids for the projects
        projects = [
            Project.query.filter_by(name=x).one_or_none() for x in project_names
        ]
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
            if project not in allowed_projects:
                raise RuntimeError(
                    f"You are not authorized to add jobs to {project} project."
                )

        # Handle the flowchart - we'll only want to add it if we're adding the job.
        flowchart_info, fl = Flowchart.parse_flowchart_file(flowchart_filename)

        try:
            flowchart = Flowchart.query.filter_by(
                sha256_strict=flowchart_info["sha256_strict"]
            ).one_or_none()
        except KeyError:
            try:
                flowchart = Flowchart.query.filter_by(
                    id=flowchart_info["id"]
                ).one_or_none()
            except KeyError:
                flowchart = None

        if flowchart is None:
            flowchart = Flowchart.create_from_file(flowchart_filename)
            flowchart.projects = projects

        if parameters is None:
            parameters = {}

        # Now add the job and update the database
        new_job = Job(
            id=id,
            title=title,
            description=description,
            path=path,
            flowchart=flowchart,
            projects=projects,
            status=status,
            submitted=submitted,
            started=started,
            finished=finished,
            parameters=parameters,
        )

        return new_job

    @classmethod
    def update(
        cls,
        id,
        description=None,
        title=None,
        path=None,
        submitted=None,
        started=None,
        finished=None,
        status=None,
        project_names=None,
    ):
        """Update method for existing jobs"""

        possible_updates = [
            "description",
            "title",
            "path",
            "submitted",
            "started",
            "finished",
            "status",
            "projects",
        ]

        job = cls.permissions_query("update").filter(Job.id == id).one_or_none()

        if job is None:
            raise ValueError(
                f"Cannot update job with id {id}. User does not have permissions, or job does not exist in the database."  # noqa: E501
            )

        projects = None

        # Check that the user has permissions for the specified projects
        if project_names is not None:
            projects = [
                Project.query.filter_by(name=x).one_or_none() for x in project_names
            ]
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
                if project not in allowed_projects:
                    raise RuntimeError(
                        f"You are not authorized to add jobs to {project} project."
                    )
        local = locals()
        update_dict = {x: local[x] for x in possible_updates if local[x] is not None}

        for k, v in update_dict.items():
            if k == "submitted" or k == "finished" or k == "started":
                if v:
                    update_dict[k] = datetime.fromtimestamp(v / 1000)
                else:
                    update_dict[k] = None

        Job.query.filter(Job.id == id).update(update_dict)

        return job

    @classmethod
    def create_from_file(cls, job_data_file):
        job_data = cls.parse_job_data(job_data_file)

        job = Job.create(job_data)

        return job


class Project(Base, Resource):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String(1000), nullable=True)
    path = Column(String, unique=True)

    flowcharts = relationship(
        "Flowchart", secondary=flowchart_project, back_populates="projects"
    )
    jobs = relationship("Job", secondary=job_project, back_populates="projects")

    def __repr__(self):
        return f"Project(name={self.name}, path={self.path}, description={self.description})"  # noqa: E501

    @classmethod
    def permissions_query(cls, permission):
        return Project.query.filter(Project.authorized(permission))

    @classmethod
    def create(cls, name, description="", path=None, group=None):
        """
        Create a project to add to the database.

        Parameters
        ----------
        name : str
            The name of the project, used for display and directory name.
        description : str
            A textual description of the project.
        path : str = None
            The path on disk to the project files.
        group : str or Group = None
            The group for the project. Defaults to user's primary group.

        Returns
        -------
        Project
            A Project object.
        """
        from flask_authorize.plugin import CURRENT_USER

        # Check that the project doesn't already exist.
        project = cls.query.filter_by(name=name).one_or_none()
        if project is not None:
            raise ValueError(
                f"Project with name {project} already found in the database"
            )

        # Sort out the user and get as a User object.

        if CURRENT_USER() is None:
            raise ValueError(
                "No user found. Log into your account to create a project."
            )
        else:
            owner = CURRENT_USER()

        # Get the group as a Group object. The default is the user's first group.
        if group is None:
            group = owner.groups[0]
        elif isinstance(group, str):
            group = Group.query.filter_by(name=group).one()

        # Create the project
        project = Project(
            name=name, description=description, path=path, owner=owner, group=group
        )

        return project

    @classmethod
    def update(
        cls,
        id,
        description=None,
        name=None,
        path=None,
    ):
        """Update method for existing jobs"""

        possible_updates = [
            "description",
            "name",
            "path",
        ]

        project = cls.permissions_query("update").filter(Project.id == id).one_or_none()

        if project is None:
            raise ValueError(
                f"Cannot update job with id {id}. User does not have permissions, or job does not exist in the database."  # noqa: E501
            )

        local = locals()
        update_dict = {x: local[x] for x in possible_updates if local[x] is not None}
        project = Project.query.get(id)

        Project.query.filter(Project.id == id).update(update_dict)
        return project
