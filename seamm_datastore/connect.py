"""
Class and functions for connection to database.
"""

import os

from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask_authorize import Authorize


def manage_session(method):
    """Decorator for closing sqlalchemy sessions."""

    @wraps(method)
    def _manage_session(self, *args, **kwargs):
        self.session = self.Session()
        ret = method(self, *args, **kwargs)
        self.session.close()
        return ret

    return _manage_session


class current_app:
    """Fake current_app"""

    def __init__(self, config):
        self.config = config
        self.extensions = ["sqlalchemy"]


class SEAMMDatastore:

    @staticmethod
    def _add_resource(resource_info, resource_type):
        resource = resource_type.query.filter_by()

    @manage_session
    def add_flowchart(self, flowchart_info):
        from .models import Flowchart

        new_flowchart = Flowchart(**flowchart_info)

        self.session.add(new_flowchart)
        self.session.commit()

    @manage_session
    def add_job(self, job_data):
        from seamm_datastore.models import Job, Project

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
            title=job_name, description=job_description, path=path, projects=[project]
        )

        self.session.add(new_job)
        self.session.commit()

    @manage_session
    def add_project(self, project_data):
        from .models import Project

        new_project = Project(**project_data)

        self.session.add(new_project)
        self.session.commit()

    @manage_session
    def get_projects(self, as_json=False):
        from .models import Project

        projects = Project.query.filter().all()

        if as_json:
            from .schema import ProjectSchema

            projects = ProjectSchema(many=True).dump(projects)

        return projects

    @manage_session
    def add_user(
            self,
            username,
            password,
            first_name=None,
            last_name=None,
            email=None,
            roles=None,
    ):

        if roles is None:
            roles = ["user"]

        # Verify username and password
        # Check if user exists
        from seamm_datastore.models import User

        user = User.query.filter_by(username=username).one_or_none()

        if user:
            raise ValueError(f"User {user} already found in the database")

        new_user = User(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

        self.session.add(new_user)
        self.session.commit()

    def login(self, username, password):
        from .models import User

        user = User.query.filter_by(username=username).one()

        if not user.verify_password(password):
            raise ValueError("Login unsuccessful. Check username and password.")

        self._user = username

    # Seems like a good place for @property, but can't use because flask authorize
    # requires this to be callable.
    def current_user(self):
        from .models import User

        if self._user:
            user = User.query.filter_by(username=self._user).one_or_none()
        else:
            user = None
        return user

    def __init__(
            self,
            database_uri: str = "sqlite:///memory:",
            initialize: bool = False,
            permissions: dict = None,
            username: str = None,
            password: str = None,
            datastore_location: str = None,
            default_project: str = "default",
    ):

        if permissions is None:
            permissions = {
                "owner": ["read", "update", "delete"],
                "group": ["read", "update"],
                "world": [],
            }

        if datastore_location is None:
            self.datastore_location = os.getcwd()
        else:
            self.datastore_location = datastore_location

        self.engine = create_engine(database_uri)
        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        global fake_app

        # Flask authorize relies on this data to be bound with the flask app
        # we'll just create a fake app and bind the data flaks authorize wants.
        fake_app = current_app(
            config={
                "AUTHORIZE_DEFAULT_PERMISSIONS": permissions,
                "AUTHORIZE_MODEL_PARSER": "table",
                "AUTHORIZE_IGNORE_PROPERTY": "__check_access__",
            }
        )

        from .models import Base, Project

        if initialize:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        Base.query = self.Session.query_property()

        if initialize:
            # Create user and add to db.
            if not username:
                raise ValueError(
                    "User and password must be given if database is being initialized."
                )
            self.add_user(username, password)

        if username:
            self.login(username, password)
        else:
            self._user = None

        # Current user has to be bound before we can add anything else to be database.
        self.authorize = Authorize(current_user=self.current_user)

        # Now handle the project
        if initialize:
            self.add_project({"name": default_project, "owner": self.current_user()})
        else:
            project = Project.query.filter_by(name=default_project).one_or_none()
            if not project:
                raise ValueError("Invalid project name given for default.")

        self.default_project = default_project
