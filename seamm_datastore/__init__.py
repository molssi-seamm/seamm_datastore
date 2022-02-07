"""
seamm_datastore
The database models for the seamm datastore
"""

# Imports - alias class to "connect".
from .connect import session_scope  # noqa: F401
from .connect import SEAMMDatastore as connect  # noqa: F401

__all__ = ["connect"]

# Handle versioneer
from ._version import get_versions

versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
