"""
Class and functions for connection to database.
"""

from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask_authorize import Authorize


def manage_session(method):
    """Decorator for closing sqlalchemy sessions."""

    @wraps(method)
    def _manage_session(self, *args, **kwargs):
        self.session = self.Session()
        method(self, *args, **kwargs)
        self.session.close()

    return _manage_session


class current_app:
    """Fake current_app"""

    def __init__(self, config):
        self.config = config
        self.extensions = ["sqlalchemy"]


class SEAMMDatastore:
    @manage_session
    def add_job(self, job_name, job_description, path, project_name):
        from seamm_datastore.models import Job, Project

        project = Project.query.filter_by(name=project_name).one_or_none()

        if not project:
            raise NameError(
                f"Project {project_name} not found in database, please check your project name."
            )

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

        projects = Project.query.filter(Project.authorized("read")).all()

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
        roles=["user"],
    ):
        print("Adding a user")

        # Verify username and password
        # Check if user exists
        from seamm_datastore.models import User

        user = User.query.filter_by("username" == username).one_or_none()

        if user:
            raise ValueError(f"User {user} already found in the database")

        new_user = User(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            roles=roles,
        )

        self.session.add(new_user)
        self.session.commit()

    def login(self, username, password):
        from .models import User

        user = User.query.filter_by(username=username).one()

        if not user.verify_password(password):
            raise ValueError("Login unsuccessful. Check username and password.")

        self._user = username

    def current_user(self):
        from .models import User

        user = User.query.filter_by(username=self._user).one()
        return user

    def __init__(
        self,
        database_uri: str="sqlite:///memory:",
        initialize: bool= False,
        permissions: dict={
            "owner": ["read", "update", "delete"],
            "group": ["read", "update"],
            "world": [],
        },
        username: str=None,
        password: str=None,
    ):

        self.engine = create_engine(database_uri)
        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        global fake_app

        fake_app = current_app(
            config={
                "AUTHORIZE_DEFAULT_PERMISSIONS": permissions,
                "AUTHORIZE_MODEL_PARSER": "table",
                "AUTHORIZE_IGNORE_PROPERTY": "__check_access__",
            }
        )

        from .models import Base, User

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

            user = User(username=username, password=password)
            self.Session.add(user)
            self.Session.commit()

        if username:
            self.login(username, password)
        else:
            self._user = None

        self.authorize = Authorize(current_user=self.current_user)
