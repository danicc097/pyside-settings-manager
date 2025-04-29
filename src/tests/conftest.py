import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def set_environment_variables():
    # pass
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
