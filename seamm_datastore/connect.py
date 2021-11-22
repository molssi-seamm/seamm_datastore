"""
Class and functions for connection to database.
"""

import os

from functools import wraps
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask_authorize import Authorize

import seamm_datastore.database.build
from seamm_datastore import api
from .util import LoginRequiredError


def manage_session(function):
    """Decorator for closing sqlalchemy sessions when attached to SEAMMDatastore
    class.
    """

    def _wrap_method(method):
        def _manage_session(self, *args, **kwargs):
            with session_scope(self.Session) as session:
                ret = function(session, as_json=True, *args, **kwargs)
            return ret

        return _manage_session

    return _wrap_method


@contextmanager
def session_scope(session):
    """Provide a transactional scope around a series of operations."""
    session = session()
    try:
        yield session
        session.commit()
    except Exception:
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
            ret = method(self, *args, **kwargs, current_user=self.current_user())
        return ret

    return _check_user


class current_app:
    """Fake current_app"""

    def __init__(self, config):
        self.config = config
        self.extensions = ["sqlalchemy"]


class SEAMMDatastore:
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

        global fake_app
        fake_app = current_app(
            config={
                "AUTHORIZE_DEFAULT_PERMISSIONS": permissions,
                "AUTHORIZE_MODEL_PARSER": "table",
                "AUTHORIZE_IGNORE_PROPERTY": "__check_access__",
            }
        )

        # Set datastore location
        if datastore_location is None:
            self.datastore_location = os.getcwd()
        else:
            self.datastore_location = datastore_location

        # Create engine and session
        self.engine = create_engine(database_uri)

        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        from seamm_datastore.database.models import Base, Project

        if initialize:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        Base.query = self.Session.query_property()

        # Set up the database.
        if initialize:
            seamm_datastore.database.build._build_initial(
                self.Session(), default_project
            )

            from seamm_datastore.database.models import Group, Role

            group = Group.query.filter_by(name="admin").one()
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
        project = Project.query.filter_by(name=default_project).one_or_none()
        if not project:
            raise ValueError("Invalid project name given for default.")

        self.default_project = default_project

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

    @manage_session(api.add_flowchart)
    def add_flowchart(self, *args, **kwargs):
        pass

    @manage_session(api.add_group)
    def add_group(self, *args, **kwargs):
        pass

    @login_required
    @manage_session(api.add_job)
    def add_job(self, *args, **kwargs):
        pass

    @login_required
    @manage_session(api.add_project)
    def add_project(self, *args, **kwargs):
        pass

    @login_required
    @manage_session(api.add_user)
    def add_user(self, *args, **kwargs):
        pass

    @login_required
    @manage_session(api.finish_job)
    def finish_job(self, *args, **kwargs):
        pass

    @manage_session(api.get_flowcharts)
    def get_flowcharts(self, *args, **kwargs):
        pass

    @manage_session(api.get_groups)
    def get_groups(self, *args, **kwargs):
        pass

    @manage_session(api.get_jobs)
    def get_jobs(self, *args, **kwargs):
        pass

    @manage_session(api.get_projects)
    def get_projects(self, *args, **kwargs):
        pass

    @manage_session(api.get_users)
    def get_users(self, *args, **kwargs):
        pass

    @manage_session(api.list_projects)
    def list_projects(self, *args, **kwargs):
        pass

    @manage_session(seamm_datastore.database.build.import_datastore)
    def import_datastore(self, *args, **kwargs):
        pass
