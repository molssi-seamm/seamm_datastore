"""
Test the create functions on the SQLAlchemy models
"""

import pytest

def test_project_create(connection):
    """Test the create method of the project object"""
    
    project = connection.Project.create(name="test_project")

    assert project.name == "test_project"
    assert project.owner == connection.current_user()

def test_project_exists(connection):

    with pytest.raises(ValueError):
        project = connection.Project.create(name="default")

def test_project_no_user(connection):

    with pytest.raises(ValueError):
        connection.logout()
        project = connection.Project.create(name="test")

def test_project_create_group(connection):
    project = connection.Project.create(name="test_project", group="molssi")

    assert project.name == "test_project"
    assert project.owner == connection.current_user()
    assert project.group.name == "molssi"

