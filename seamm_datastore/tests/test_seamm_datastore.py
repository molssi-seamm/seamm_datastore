"""
Unit and regression test for the seamm_datastore package.
"""

# Import package, test suite, and other packages as needed
import seamm_datastore
import pytest
import sys

def test_import(): 
    assert seamm_datastore in sys.modules

