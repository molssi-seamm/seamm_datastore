SEAMM Datastore
==============================
[//]: # (Badges)
[![GitHub Actions Build Status](https://github.com/molssi-seamm/seamm_datastore/workflows/CI/badge.svg)](https://github.com/molssi-seamm/seamm_datastore/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/molssi-seamm/seamm_datastore/branch/master/graph/badge.svg)](https://codecov.io/gh/molssi-seamm/seamm_datastore/branch/master)


This repository contains the SQLAlchemy models for the SEAMM datastore as well as some associated utilities such as dumping to JSON and checking permissions. These database models and permissions system were developed to be used inside a flask application context in the [SEAMM Dashboard](https://github.com/molssi-seamm/seamm_dashboard). However, you may use this package as a stand-alone (outside of flask) with limited permissions capabilities.

## Quickstart

This package contains SQLAlchemy models for the SEAMM datastore. The following gives an example of how to connect to a database in memory. You can switch the database by providing a different database URI.

```python
import seamm_datastore

# Create a database session
connection = seamm_datastore.connect("sqlite:///:memory:")
```
This will create a sqlite database stored in memory. Using `initialize=True` will result in a new database being created. You may substitute a different database URI in place of `sqlite:///memory`. When connecting to a database on disk, you will need to specify an additional argument, `initialize=True`, if creating a new database.

To login, use the login method. Your username is determined automatically by your username when running `connect` if `initialize` is `True.` An admin user is also create which you can use to login (username=`admin`, password=`admin`).

```python
connection.login(username="YOUR_USERNAME", password="default")
```

To import a datastore at a particular location, do:

```python
connection.import_datastore(FILEPATH)
```

To use the sample data in this repository,

```python
jobs, projects = connection.import_datastore("seamm_datastore/data/Projects")
```

JSON data of the added jobs and projects will be returned.

The `SEAMMDatastore` class has bound database models and a SQLAlchemy session factory which you can work with. These can be interacted with the same as other sqlalchemy models. To retrieve jobs for which you have "read" permissions from the database, use the bound SQLAlchemy models:

```
jobs = connection.Job.permissions_query("read").all()
```

To dump to json:

```python
from seamm_datastore.database.schema import JobSchema

# Create job schema
jobs_schema = JobSchema(many=True)

# To retrieve all users in db
all_jobs = connection.Job.permissions_query("read").all()

jobs_json = jobs_schema.dump(all_jobs)
```

## Permissions

The SEAMM datastore has a permissions system built in using [flask-authorize](https://flask-authorize.readthedocs.io/en/latest/) for authorization. This provides a "permissions" entry on each resource table (Jobs, Flowcharts, and Projects) where permissions for "owner", "group" and "world". The SEAMM datastore also has capabilities to set "special permissions" for users or groups on specific projects.

Permissions are not automatically enforced when working directly with database models. In the SEAMM Dashboard, permissions are enforced with **authentication** (verifying the user is who they say they are) using [flask-jwt-extended] and **authorization** using [flask-authorize](https://flask-authorize.readthedocs.io/en/latest/). 

To use the permissions checking mechanisms of flask authorize outside of a flask app, use the helper function here `seamm_datastore.SEAMMDatastore`.

### Copyright

Copyright (c) 2021, Jessica A. Nash (The Molecular Sciences Software Institute)


#### Acknowledgements
 
Project based on the 
[Computational Molecular Science Python Cookiecutter](https://github.com/molssi/cookiecutter-cms) version 1.5.
