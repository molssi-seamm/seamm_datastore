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


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_group, back_populates="groups")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary=user_role, back_populates="roles")


class Flowchart(Base, AccessControlPermissionsMixin):
    __tablename__ = "flowcharts"

    id = Column(Integer, nullable=False, primary_key=True)
    sha256 = Column(String(75), nullable=True)
    sha256_strict = Column(String(75), nullable=True)
    path = Column(String, nullable=True)
    flowchart_version = Column(Float, nullable=True, unique=False)
    doi = Column(Text, nullable=True)
    title = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    creators = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    json = Column(JSON, nullable=False)

    jobs = relationship("Job", back_populates="flowchart", lazy=True)
    projects = relationship(
        "Project", secondary=flowchart_project, back_populates="flowcharts"
    )

    def __repr__(self):
        return f"Flowchart(id={self.id}, description={self.description}, path={self.path})"  # noqa: E501


class Job(Base, AccessControlPermissionsMixin):
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

class Project(Base, AccessControlPermissionsMixin):
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
    def create(cls, name, description="", path=None, owner=None, group=None, as_json=False):
        """
        Create a project to add to the database.

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
        Project
            A Project object.
        """
        from flask_authorize.plugin import CURRENT_USER

        # Check that the project doesn't already exist.
        project = cls.query.filter_by(name=name).one_or_none()
        if project is not None:
            raise ValueError(f"Project {project} already found in the database")

        # Sort out the user and get as a User object.
        if owner is None:
            if CURRENT_USER is None:
                raise ValueError("The owner is required for adding a project. No owner specified or user logged in.")
            else:
                owner = CURRENT_USER()
        if isinstance(owner, str):
            owner = User.query.filter_by(username=owner).one()

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



############################
#
# Special Model Methods
#
###########################

# Add a "permissions query" function to be added to flowcharts and jobs
# For both of these items, permissions must be checked on the
# resource itself (job or flowchart)mand on projects containing the resource.

from seamm_datastore.database.special import _create_project


def _permissions_query(resource):
    def inner(permission):
        self_read = resource.query.filter(resource.authorized(permission))
        self_projects = resource.query.filter(
            resource.projects.any(Project.authorized(permission))
        )
        return self_read.union(self_projects)

    return inner


def _role_query(resource):
    def inner(role):
        from flask_authorize.plugin import CURRENT_USER
        from seamm_datastore.util import NotAuthorizedError

        role_names = [x.name for x in CURRENT_USER.roles]

        if role not in role_names:
            raise NotAuthorizedError
        else:
            return User.query

    return inner


Job.permissions_query = _permissions_query(Job)
Flowchart.permissions_query = _permissions_query(Flowchart)

User.role_query = _role_query(User)

#Project.create = _add_project
