"""

CRUD (create, read, update, delete) functions for the database.

To be used with datastore connection or with seamm dashboard. These functions
are meant to provide basic interaction with database. If you need to do something
more specific, use the database models directly.

"""

import inspect

from copy import deepcopy

def _add_resource(resource, session, **resource_info):

    to_add = resource.create(**resource_info)

    session.add(to_add)
    sesiion.commit()

def add_job(session, job_id,
        flowchart_filename,
        project_names=["default"],
        path=None,
        title="",
        description="",
        submitted=None,
        started=None,
        finished=None,
        status="submitted",

        as_json=False
    ):

    argspect = inspect.getfullargspec(add_job)
    
    var = locals()

    function_args = { k : var[k] for k in argspect[0] }

    function_args.pop("session")
    function_args.pop("as_json")
    
    from seamm_datastore.database.models import Job

    job = Job.create(**function_args)

    session.add(job)
    session.commit()

    return job
