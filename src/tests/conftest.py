import os
import pytest
from pytestqt.qtbot import QtBot


@pytest.fixture(autouse=True, scope="session")
def set_environment_variables():
    # pass
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


def qtbot(qapp, request):
    result = QtBot(request)
    return result
