seamm_datastore
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
connection = seamm_datastore.SEAMMDatastore("sqlite:///:memory:", initialize=True, username="your_username", password="your_password")
```

The `SEAMMDatastore` class has associated functions which can be used to add to the database using the same permission system that the seamm dashboard uses. Use the `.add_job` method to add a job and `get_jobs` to get all of the jobs the user is authorized to view.

To retrieve all the users and dump the info to JSON:

```python
from seamm_datastore.database.schema import JobSchema

# Create user schema
users = JobSchema(many=True)

# To retrieve all users in db
all_jobs = connection.get_jobs()

users_json = users.dump(all_jobs)
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
