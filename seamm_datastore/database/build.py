"""
Automatic import of projects and jobs from directories.
"""

import os
import json
from pathlib import Path

from datetime import datetime

from seamm_datastore import api

time_format = "%Y-%m-%d %H:%M:%S %Z"


def import_datastore(session, location, as_json=True):
    """Import all the projects and jobs at <location>.

    Parameters
    ----------
    session : SQLAlchemy or flask session
    location : str or path
        The location to check for jobs or projects. Usually the projects directory in a datastore.

    Returns
    -------
    (n_projects, n_jobs) : int, integer
        The number of projects and jobs added to the database.
    """

    jobs = []
    projects = []

    # Get directory contents of file path
    for folder in os.listdir(location):
        potential_project = os.path.join(location, folder)

        # If item is a directory, it may contain jobs.
        # We are going to be taking the project names
        # from the job_data.json
        if os.path.isdir(potential_project):
            project_name = os.path.basename(potential_project)
            item = Path(potential_project)
            group = item.group()
            username = item.owner()
            project_data = {
                "owner": username,
                "group": group,
                "name": project_name,
                "path": potential_project,
            }

            try:
                project = api.add_project(session, project_data, as_json=as_json)
                projects.append(project)
            except ValueError:
                # Project exists, we don't need to add it.
                # Pass here because we should still try importing jobs.
                pass

            for potential_job in os.listdir(potential_project):
                potential_job = os.path.join(potential_project, potential_job)

                if os.path.isdir(potential_job):
                    job_name = os.path.basename(potential_job)

                    # Check for job_data.json - has to have this to be job
                    check_path = os.path.join(potential_job, "job_data.json")

                    if os.path.exists(check_path):
                        with open(check_path) as f:
                            job_data_json = json.load(f)
                        job_data = {
                            "path": potential_job,
                            "title": str(
                                job_data_json["title"]
                                if job_data_json["title"]
                                else job_name
                            ),
                            "project_names": job_data_json["projects"],
                            "status": job_data_json["state"],
                        }

                        if "end time" in job_data_json:
                            job_data["finished"] = datetime.strptime(
                                job_data_json["end time"], time_format
                            )

                        if "start time" in job_data_json:

                            job_data["started"] = datetime.strptime(
                                job_data_json["start time"], time_format
                            )

                        try:
                            job = api.add_job(
                                session, job_data=job_data, as_json=as_json
                            )
                            jobs.append(job)
                        except ValueError:
                            # Job has already been added.
                            # Continue here - go to next job
                            continue

        return jobs, projects
