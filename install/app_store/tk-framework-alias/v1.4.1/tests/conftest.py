import pytest
import os
import sys
import datetime
import os


###############################################################################
# pytest configuration
###############################################################################


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """

    print("Configuring...")

    # import debugpy
    # debugpy.listen(5678)
    # debugpy.wait_for_client()
    # # debugpy.breakpoint()

    # Add the python modules to the sys.path for import
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
    tk_framework_alias = os.path.abspath(os.path.join(base_dir, "tk_framework_alias"))
    tk_framework_alias_utils = os.path.abspath(
        os.path.join(base_dir, "tk_framework_alias_utils")
    )
    sys.path.extend(
        [
            base_dir,
            tk_framework_alias,
            tk_framework_alias_utils,
        ]
    )

    # TODO run tests for all supported api?
    # Set up the environment
    os.environ["ALIAS_PLUGIN_CLIENT_ALIAS_VERSION"] = "2024.0"


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """

    print("Timestamp:  {}".format(datetime.datetime.now()))

    from tk_framework_alias.server.api import alias_api

    print(
        "Alias API Python {mode}".format(
            mode="OpenModel" if alias_api.__open_model__ else "OpenAlias"
        )
    )
    print("\tv{}".format(alias_api.__version__))
    print("\tAlias v{}".format(alias_api.__alias_version__))
    print("\tPython v{}".format(sys.version))
    print("\tPython exe: {}".format(sys.executable))
    print("\t{}".format(alias_api.__file__))

    # Ensure Alias Universe is already initialized and ready.
    alias_api.initialize_universe()


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """


def pytest_unconfigure(config):
    """
    called before test process is exited.
    """


###############################################################################
# Global Fixtures
###############################################################################


@pytest.fixture(scope="session")
def scripts_path(request):
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "scripts",
        )
    )


@pytest.fixture(scope="session")
def client_exe_path(scripts_path):
    return os.path.abspath(os.path.join(scripts_path, "bootstrap_client_test.py"))


@pytest.fixture(scope="session")
def start_server_script_path(scripts_path):
    return os.path.abspath(os.path.join(scripts_path, "start_server.py"))
