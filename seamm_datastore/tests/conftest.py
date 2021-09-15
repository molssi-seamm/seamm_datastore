"""
Fixtures for testing
"""

import pytest
import seamm_datastore

@pytest.fixture(scope="function")
def connection():
    db = seamm_datastore.connect(
        initialize=True, username="test_user", password="password"
    )
    return db
