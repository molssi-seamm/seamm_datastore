# -*- coding: utf-8 -*-

"""Build a datastore from the job directories on disk.

The job directories are the record of what ran: each holds its flowchart and a
``job_data.json``. A datastore can therefore be made again from them -- when the
database file is missing, or to replace one that no longer matches the disk.
"""

import getpass
import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)

# The tables of accounts, copied whole from the datastore being replaced
_ACCOUNT_TABLES = ("users", "groups", "roles", "user_group", "user_role")


def job_directories(projects_path):
    """The job directories (those with a job_data.json) under a projects directory.

    Parameters
    ----------
    projects_path : str or Path
        E.g. <root>/Jobs/projects.

    Returns
    -------
    [Path]
    """
    projects_path = Path(projects_path)
    if not projects_path.is_dir():
        return []
    return sorted(p.parent for p in projects_path.glob("*/*/job_data.json"))


def build_from_jobs(
    db_path,
    projects_path=None,
    username=None,
    keep_from=None,
    default_project="default",
):
    """Create a datastore from the job directories on disk.

    Parameters
    ----------
    db_path : str or Path
        The datastore to create. It must not exist yet.
    projects_path : str or Path, optional
        The directory holding the projects and their jobs; by default the
        ``projects`` directory beside the datastore.
    username : str, optional
        The account that owns what is imported (when ``keep_from`` does not say
        otherwise). By default the account named like the user running this, if
        there is one, else 'admin'.
    keep_from : str or Path, optional
        A datastore being replaced. Its accounts (users, groups and roles) are kept,
        as are the owners, groups, permissions and descriptions of projects that
        still exist, and the owner and permissions of each job that is imported
        again.
    default_project : str
        The name of the default project.

    Returns
    -------
    dict
        The numbers of projects and jobs imported.
    """
    import seamm_datastore

    db_path = Path(db_path)
    if db_path.exists():
        raise FileExistsError(f"The datastore {db_path} already exists.")
    if projects_path is None:
        projects_path = db_path.parent / "projects"
    projects_path = Path(projects_path)
    projects_path.mkdir(parents=True, exist_ok=True)

    datastore = seamm_datastore.connect(
        database_uri=f"sqlite:///{db_path}",
        datastore_location=str(db_path.parent),
        initialize=True,
        default_project=default_project,
    )

    # Only after connect(): the models pick up its stand-in for a Flask application
    # the first time they are imported.
    from seamm_datastore.database.models import User

    if keep_from is not None:
        # The accounts of the datastore being replaced, instead of the defaults
        datastore.Session.remove()
        db = sqlite3.connect(str(db_path))
        with db:
            db.execute("attach database ? as old", (str(keep_from),))
            for table in reversed(_ACCOUNT_TABLES):
                db.execute(f"delete from {table}")
            for table in _ACCOUNT_TABLES:
                db.execute(f"insert into {table} select * from old.{table}")
        db.execute("detach database old")
        db.close()
        datastore.Session.remove()

    if username is None:
        me = getpass.getuser()
        username = (
            me
            if User.query.filter_by(username=me).one_or_none() is not None
            else "admin"
        )
    datastore._user = username
    try:
        jobs, projects = datastore.import_datastore(str(projects_path))
    finally:
        datastore._user = None
        datastore.Session.remove()

    if keep_from is not None:
        db = sqlite3.connect(str(db_path))
        with db:
            db.execute("attach database ? as old", (str(keep_from),))
            # Projects that still exist keep their details
            db.execute("""
                update projects set
                    description = o.description,
                    owner_id = o.owner_id,
                    group_id = o.group_id,
                    owner_permissions = o.owner_permissions,
                    group_permissions = o.group_permissions,
                    other_permissions = o.other_permissions
                from old.projects as o where o.name = projects.name
                """)
            for table in ("users_projects_association", "groups_projects_association"):
                db.execute(f"""
                    insert into {table} (permissions, entity_id, resource_id)
                    select a.permissions, a.entity_id, p.id
                    from old.{table} a
                    join old.projects op on op.id = a.resource_id
                    join projects p on p.name = op.name
                    """)
            # Jobs keep their owner and permissions
            db.execute("""
                update jobs set
                    owner_id = o.owner_id,
                    group_id = o.group_id,
                    owner_permissions = o.owner_permissions,
                    group_permissions = o.group_permissions,
                    other_permissions = o.other_permissions
                from old.jobs as o where o.id = jobs.id
                """)
        db.execute("detach database old")
        db.close()

    return {"projects": len(projects), "jobs": len(jobs)}
