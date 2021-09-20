"""
Fixtures for testing
"""

import pytest
import seamm_datastore

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture()
def session():
    some_engine = create_engine('sqlite:///:memory:')

    # create a configured "Session" class
    Session = sessionmaker(bind=some_engine)

    # create a Session
    sess = Session()
    return sess

@pytest.fixture(scope="function")
def connection():
    db = seamm_datastore.connect(
        initialize=True
    )
    db.login(username="admin", password="admin")
    return db
