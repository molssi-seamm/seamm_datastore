"""
Fixtures for testing
"""

import pytest
import seamm_datastore

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def session():
    some_engine = create_engine("sqlite:///:memory:")

    # create a configured "Session" class
    Session = sessionmaker(bind=some_engine)

    # create a Session
    sess = Session()
    return sess


@pytest.fixture(scope="function")
def connection():
    from seamm_datastore import session_scope

    db = seamm_datastore.connect(initialize=True)

    with session_scope(db.Session) as _:
        from seamm_datastore.database.models import User

        users = User.query.all()
        for data in users:
            if data.username != "admin":
                user = data.username
                break
    db.login(username=user, password="default")
    return db


@pytest.fixture(scope="function")
def admin_connection(connection):
    connection.login(username="admin", password="admin")

    return connection
