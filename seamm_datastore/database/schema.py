"""
Marshmallow models for serialization and deserialization.

"""

import datetime

from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Related, Nested

from seamm_datastore.database.models import Flowchart, Project, Job, User, Group, Role

#############################
#
# Custom Field
#
#############################


class LocalDateTime(fields.DateTime):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        data_format = self.format or self.DEFAULT_FORMAT
        value = value.replace(tzinfo=datetime.timezone.utc)
        value = value.astimezone()
        return value.strftime(data_format)


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
            "sha256",
        )

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
    started = LocalDateTime(format="%Y-%m-%d %H:%M")
    finished = LocalDateTime(format="%Y-%m-%d %H:%M")
    submitted = LocalDateTime(format="%Y-%m-%d %H:%M")
    last_update = LocalDateTime(format="%Y-%m-%d %H:%M")


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
