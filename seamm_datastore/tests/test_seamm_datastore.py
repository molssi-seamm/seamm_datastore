"""
Unit and regression test for the seamm_datastore package.
"""


def test_connected(admin_connection):
    assert admin_connection.current_user().username == "admin"
    assert admin_connection.default_project == "default"


def test_connection_logout(connection):
    connection.logout()
    assert connection.current_user() is None
