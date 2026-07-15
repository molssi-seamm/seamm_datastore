"""
Class and functions for connection to database.
"""

import os
import time

from functools import wraps
from contextlib import contextmanager
from warnings import warn

from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import scoped_session, sessionmaker

from flask_authorize import Authorize

import seamm_datastore.database.build
from .util import LoginRequiredError


def manage_session(function):
    """Decorator for closing sqlalchemy sessions when attached to SEAMMDatastore
    class.
    """

    def _wrap_method(method):
        def _manage_session(self, *args, **kwargs):
            with session_scope(
                self.Session, timeout=getattr(self, "timeout", 20.0)
            ) as session:
                ret = function(session, as_json=True, *args, **kwargs)
            return ret

        return _manage_session

    return _wrap_method


@contextmanager
def session_scope(session, timeout=20.0):
    """Provide a transactional scope around a series of operations.

    Parameters
    ----------
    session : callable
        A session factory (e.g. a ``scoped_session``) returning a new session.
    timeout : float
        Seconds to keep retrying the commit while the (SQLite) database is
        locked by another process. Together with the connection-level
        ``PRAGMA busy_timeout`` this lets many jobs register in the datastore
        at the same time -- e.g. a batch of SLURM jobs starting together --
        without failing with "database is locked". Default: 20 s.
    """
    session = session()
    try:
        yield session
        _commit_with_retry(session, timeout)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _commit_with_retry(session, timeout):
    """Commit, retrying while the database is locked, up to ``timeout`` seconds.

    On SQLite a COMMIT that fails with ``SQLITE_BUSY`` leaves the transaction
    open, so the pending work is retried by simply calling ``commit`` again --
    we deliberately do *not* roll back between attempts. This backs up the
    connection's ``PRAGMA busy_timeout`` for the case (e.g. a shared network
    filesystem) where the busy handler is not honoured and BUSY is returned
    immediately.
    """
    deadline = time.monotonic() + max(0.0, timeout)
    delay = 0.1
    while True:
        try:
            session.commit()
            return
        except OperationalError as e:
            if "database is locked" not in str(e).lower():
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, 2.0)


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
        timeout: float = 20.0,
    ):
        if database_uri.lower() == "sqlite:///:memory:":
            initialize = True

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
        self.timeout = timeout
        self.engine = create_engine(database_uri)

        # For a file-based SQLite database, wait (rather than failing
        # immediately) when another process holds the write lock. This lets
        # many jobs register in the datastore at the same time, e.g. when a
        # batch of SLURM jobs start together.
        if "sqlite" in database_uri.lower() and ":memory:" not in database_uri.lower():
            busy_ms = int(max(0.0, timeout) * 1000)

            @event.listens_for(self.engine, "connect")
            def _set_sqlite_busy_timeout(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute(f"PRAGMA busy_timeout={busy_ms}")
                cursor.close()

        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        from seamm_datastore.database.models import (
            Base,
            Project,
            User,
            Job,
            Group,
            Role,
            Flowchart,
        )

        if initialize:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        Base.query = self.Session.query_property()

        # Set up the database.
        if initialize:
            seamm_datastore.database.build._build_initial(
                self.Session(), default_project
            )

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

        self.User = User
        self.Group = Group
        self.Role = Role
        self.Project = Project
        self.Job = Job
        self.Flowchart = Flowchart

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

    @manage_session(seamm_datastore.database.build.import_datastore)
    def import_datastore(self, *args, **kwargs):
        pass

    def add_job(
        self,
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
        warn(
            "Deprecation warning: This method will no longer be available",
            " in the next version of the seamm datastore.",
            " Job.create should be used instead.",
        )

        if parameters is None:
            parameters = {"cmdline": []}

        with session_scope(
            self.Session, timeout=getattr(self, "timeout", 20.0)
        ) as session:
            job = self.Job.create(
                id,
                flowchart_filename,
                project_names,
                path,
                title,
                description,
                submitted,
                started,
                finished,
                parameters,
                status,
            )

            session.add(job)

    def finish_job(
        self,
        job_id,
        finish_time,
        status="finished",
    ):
        """Set the status and time that the job finished.

        Parameters
        ----------
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
        warn("Deprecation warning: This method will no longer be available \
            in the next version of the seamm datastore. \
            Job.update should be used instead.")

        from seamm_datastore.database.models import Job

        with session_scope(
            self.Session, timeout=getattr(self, "timeout", 20.0)
        ) as session:
            job = Job.get_by_id(job_id, permission="update")

            if job is None:
                return False
            else:
                job.finished = finish_time
                job.status = status
                session.commit()
                return True
