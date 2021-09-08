"""
Marshmallow models for serialization and deserialization.

"""

from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import marshmallow_sqlalchemy
from marshmallow_sqlalchemy.fields import Related, Nested

from .models import Flowchart, Project, Job, User, Group, Role

#############################
#
# Marshmallow Schema
#
#############################


class FlowchartSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = Flowchart
        exclude = (
            "json",
            "owner_permissions",
            "group_permissions",
            "other_permissions",
            "sha256"
        )
    name = fields.String(data_key="title")

    owner = Related("username")
    group = Related("name")


class ProjectSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = Project
        exclude = ("owner_permissions", "group_permissions", "other_permissions")

    owner = Related("username")
    group = Related("name")


class JobSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = Job
        exclude = (
            "flowchart",
            "owner_permissions",
            "group_permissions",
            "other_permissions",
        )

    owner = Related("username")
    group = Related("name")
    projects = Nested(
        ProjectSchema(
            only=(
                "name",
                "id",
            ),
            many=True,
        )
    )


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = User
        exclude = ("password_hash",)


class GroupSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = Group

    users = Nested(
        UserSchema(
            only=(
                "username",
                "id",
            ),
            many=True,
        )
    )


class RoleSchema(SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        include_relationships = True
        model = Role
