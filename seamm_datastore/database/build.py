"""
Automatic import of projects and jobs from directories.
"""

import os
from pathlib import Path


def _build_initial(session, default_project):
    """Build the initial database"""

    from seamm_datastore.database.models import Role, Group, User, Project

    # Create roles
    role_names = ["user", "group manager", "admin"]
    for role_name in role_names:
        role = Role(name=role_name)
        session.add(role)
        session.commit()

    # Create default admin group
    admin_group = Group(name="admin")
    session.add(admin_group)
    session.commit()

    # Create default admin user.s
    admin_role = session.query(Role).filter_by(name="admin").one()
    admin_user = User(username="admin", password="admin", roles=[admin_role])
    admin_user.groups.append(admin_group)

    # Create a user and group with the same information as user running
    try:
        item = Path.home()
        username = item.owner()
        group_name = item.group()
    except NotImplementedError:
        # This will occur on Windows
        import os

        username = os.environ["USERNAME"]
        # Just a default group name.
        group_name = "staff"

    group = Group(name=group_name)

    password = "default"
    user = User(username=username, password=password, roles=[admin_role])
    user.groups.append(group)

    # Admin user needs to be part of all groups.
    admin_user.groups.append(group)

    session.add(admin_user)
    session.add(admin_role)
    session.add(admin_group)

    session.add(user)

    # Create a default project
    project = Project(name=default_project, owner=user, group=group)
    session.add(project)
    session.commit()


def import_datastore(session, location, as_json=True):
    """Import all the projects and jobs at <location>.

    Parameters
    ----------
    session : SQLAlchemy or flask session
    location : str or path
        The location to check for jobs or projects. Usually the projects directory in a
        datastore.

    Returns
    -------
    (n_projects, n_jobs) : int, integer
        The number of projects and jobs added to the database.
    """

    from seamm_datastore.database.models import Project, Job

    jobs = []
    project_names = []

    # Get directory contents of file path
    for folder in os.listdir(location):
        potential_project = os.path.join(location, folder)

        # If item is a directory, it may contain jobs.
        # We are going to be taking the project names
        # from the job_data.json
        if os.path.isdir(potential_project):
            project_name = os.path.basename(potential_project)
            item = Path(potential_project)
            try:
                group = item.group()
                username = item.owner()
            except NotImplementedError:
                username = os.environ["USERNAME"]
                # Just a default group name.
                group = "staff"

            project_data = {
                "owner": username,
                "group": group,
                "name": project_name,
                "path": potential_project,
            }

            try:
                project = Project.create(
                    name=project_name,
                    path=potential_project,
                    group=group,
                )
                session.add(project)
                session.commit()
            except ValueError:
                # Project already in DB
                print(
                    f"Project {project_name} not imported because it is "
                    "already in the database."
                )
                session.rollback()

            project_names.append(project_data["name"])

            for potential_job in os.listdir(potential_project):
                potential_job = os.path.join(potential_project, potential_job)

                if os.path.isdir(potential_job):
                    # Check for job_data.json - has to have this to be job
                    check_path = os.path.join(potential_job, "job_data.json")
                    if os.path.exists(check_path):
                        try:
                            job_data = Job.parse_job_data(check_path)
                        except Exception as e:
                            print(f"Could not read the job data {check_path}: {str(e)}")
                        else:
                            if "command line" in job_data:
                                parameters = {"cmdline": job_data["command line"]}
                            else:
                                parameters = {"cmdline": []}

                            try:
                                job = Job.create(
                                    job_data["id"],
                                    potential_job + "/flowchart.flow",
                                    project_names=job_data["project_names"],
                                    path=potential_job,
                                    title=job_data["title"],
                                    description=job_data.get("description", ""),
                                    submitted=job_data.get("submitted", None),
                                    started=job_data.get("started", None),
                                    finished=job_data.get("finished", None),
                                    status=job_data["status"],
                                    parameters=parameters,
                                )
                            except Exception:
                                print(
                                    f"Job {job_data['id']} not imported because it is "
                                    "already in the database."
                                )
                            else:
                                session.add(job)
                                session.commit()
                                jobs.append(job)

    session.commit()

    # retrieve projects now that all the jobs have been added.
    projects = Project.query.filter(Project.name.in_(project_names)).all()

    if as_json is True:
        from seamm_datastore.database.schema import ProjectSchema, JobSchema

        jobs = JobSchema(many=True).dump(jobs)
        projects = ProjectSchema(many=True).dump(projects)

    return jobs, projects
