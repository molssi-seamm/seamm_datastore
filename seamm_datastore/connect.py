"""
Class and functions for connection to database.
"""

import os

from functools import wraps
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask_authorize import Authorize


from .util import LoginRequiredError, _build_initial


def manage_session(method):
    """Decorator for closing sqlalchemy sessions."""

    @wraps(method)
    def _manage_session(self, *args, **kwargs):
        session = Session()
        try:
            ret = method(self, *args, **kwargs)
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return ret

    return _manage_session

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def login_required(method):
    """Decorator for actions requiring current user"""

    @wraps(method)
    def _check_user(self, *args, **kwargs):
        if not self.current_user():
            raise LoginRequiredError

        else:
            ret = method(self, *args, **kwargs)
        return ret

    return _check_user


class current_app:
    """Fake current_app"""

    def __init__(self, config):
        self.config = config
        self.extensions = ["sqlalchemy"]


class SEAMMDatastore:

    def add_flowchart(self, flowchart_info):

        from seamm_datastore.database.models import Flowchart

        new_flowchart = Flowchart(**flowchart_info)

        self.session.add(new_flowchart)
        self.session.commit()

    @login_required
    @manage_session
    def add_job(self, job_data):
        """Add a job to the datastore.

        This method requires a user to be logged in and to have appropriate permissions
        for the project.
        """
        from seamm_datastore.database.models import Job, Project

        try:
            project_name = job_data["project_name"]
            project = Project.query.filter_by(name=project_name).one_or_none()

            if not project:
                raise NameError(
                    f"Project {project_name} not found in database, please check your project name."
                )

        # If no project name, add to default project
        except KeyError:
            project = Project.query.filter_by(name="default").one()

        # The other permissions method in flask-authorize is harder to fake,
        # but this one works.
        if project not in Project.query.filter(Project.authorized("update")).all():
            raise RuntimeError("You are not authorized to add jobs to this project.")

        new_job = Job(
            title=job_data["name"],
            description=job_data["description"],
            path=job_data["path"],
            projects=job_data["projects"],
        )

        self.session.add(new_job)
        self.session.commit()

    @login_required
    @manage_session
    def add_project(self, project_data):
        from seamm_datastore.database.models import Project

        new_project = Project(**project_data)

        self.session.add(new_project)
        self.session.commit()

    @manage_session
    def get_projects(self, as_json=False):
        from seamm_datastore.database.models import Project

        projects = Project.query.filter(Project.authorized("read")).all()

        if as_json:
            from seamm_datastore.database.schema import ProjectSchema

            projects = ProjectSchema(many=True).dump(projects)

        return projects

    @login_required
    @manage_session
    def add_user(
            self,
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

        self.session.add(new_user)
        self.session.commit()

    def login(self, username, password):
        from seamm_datastore.database.models import User

        user = User.query.filter_by(username=username).one()

        if not user.verify_password(password):
            raise ValueError("Login unsuccessful. Check username and password.")

        self._user = username

    def logout(self):
        self._user = None

    # Seems like a good place for @property, but can't use because flask authorize
    # requires this to be callable.
    def current_user(self):
        from seamm_datastore.database.models import User

        if self._user:
            user = User.query.filter_by(username=self._user).one_or_none()
        else:
            user = None
        return user

    def __init__(
            self,
            database_uri: str = "sqlite:///:memory:",
            initialize: bool = False,
            permissions: dict = None,
            username: str = None,
            password: str = None,
            datastore_location: str = None,
            default_project: str = "default",
    ):

        # Default permissions
        if permissions is None:
            permissions = {
                "owner": ["read", "update", "delete"],
                "group": ["read", "update"],
                "world": [],
            }

        # Set datastore location
        if datastore_location is None:
            self.datastore_location = os.getcwd()
        else:
            self.datastore_location = datastore_location


        # Create engine and session
        self.engine = create_engine(database_uri)

        # SQLAlchemy recommends a global session. We only want one if we're not
        # using flask. We'll make the restriction that when using SQLAlchemy only,
        # we should always use this object (this will hold datastore location and
        # the logged in user.
        global Session
        Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        from seamm_datastore.database.models import Base, Project

        if initialize:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        Base.query = self.Session.query_property()

        # Set up the database.
        if initialize:
            _build_initial(self.Session())

            from seamm_datastore.database.models import Group, Role
            group = Group.query.one()
            admin_role = Role.query.filter_by(name="admin").one()

            # Log in the admin user and create specified user
            if username:
                self.login("admin", "admin")
                self.add_user(username, password, roles=[admin_role], groups=[group])
                self.logout()

        if username:
            self.login(username, password)
        else:
            self._user = None

        # Current user has to be bound before we can add anything else to be database.
        self.authorize = Authorize(current_user=self.current_user)

        # Now handle the project
        if initialize:
            self.add_project({"name": default_project, "owner": self.current_user(), "group": group})
        else:
            project = Project.query.filter_by(name=default_project).one_or_none()
            if not project:
                raise ValueError("Invalid project name given for default.")

        self.default_project = default_project


