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
