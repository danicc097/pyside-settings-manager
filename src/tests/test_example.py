# tests/test_example_basic.py

import sys
import os
import pytest
import logging
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from examples.basic import MyWindow, LogWindow, setup_logging

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from PySide6.QtTest import QSignalSpy

from pytestqt.qtbot import QtBot

from pyside_settings_manager.settings import (
    create_settings_manager,
    SettingsManager,
    CUSTOM_DATA_GROUP,
)

WAIT_TIMEOUT = 5_000  # Reduce timeout for faster feedback on failures
WAIT_INTERVAL = 50  # Small interval for minor event loop processing if needed

# Increase logging level in tests to debug for better visibility
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d - %(levelname)-7s - [%(name)s:%(lineno)d] %(message)s",
)
# Suppress noisy loggers
logging.getLogger("PySide6.QtOpenGL").setLevel(logging.WARNING)
logging.getLogger("PySide6.QtGui").setLevel(logging.INFO)
logging.getLogger("PySide6.QtCore.QFileSystemWatcher").setLevel(logging.WARNING)


@pytest.fixture
def example_settings_file(tmp_path: Path) -> str:
    """Provides a temporary file path for the example app's settings."""
    fpath = tmp_path / "test_example_app_settings.ini"
    fpath_str = str(fpath)
    # Ensure cleanup happens even if previous test failed
    if os.path.exists(fpath_str):
        try:
            os.remove(fpath_str)
        except OSError as e:
            logging.warning(f"Could not remove settings file {fpath_str}: {e}")
    # Also ensure the directory exists for the file watcher
    os.makedirs(os.path.dirname(fpath_str), exist_ok=True)
    return fpath_str


@pytest.fixture
def example_manager(example_settings_file: str) -> SettingsManager:
    """Creates a settings manager using the example's temp file."""
    settings = QSettings(example_settings_file, QSettings.Format.IniFormat)
    manager = create_settings_manager(settings)
    # We need to keep a reference to settings or it might get GC'd prematurely in tests
    manager._test_settings_ref = settings  # type: ignore
    return manager


@pytest.fixture
def example_window(
    qtbot: QtBot, example_manager: SettingsManager, example_settings_file: str
) -> MyWindow:
    """Creates the main window from the example."""
    # Keep a reference to the manager for clarity
    manager = example_manager

    # Create the window. Its __init__ will call _update_settings_file_display once.
    window = MyWindow(manager=manager, settings_file_path=example_settings_file)

    # Setup logging...
    log_handler = setup_logging(window.log_window)
    window.log_window.hide()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)  # Ensure window is visible and ready

    # Perform the initial load from the manager.
    # This applies default settings (since file doesn't exist) to widgets.
    # It does NOT trigger window.settings_file_display_updated by itself.
    # The initial update happened in window.__init__.
    logging.info("Performing initial load...")
    manager.load()

    # After loading defaults, the manager state should be 'untouched'.
    # Wait for this state to be stable.
    logging.info("Waiting for manager state to stabilize after load...")
    qtbot.waitUntil(lambda: not manager.is_touched, timeout=WAIT_TIMEOUT)

    # At this point:
    # 1. Window is created and shown.
    # 2. _update_settings_file_display ran once during __init__ (signal emitted then).
    # 3. manager.load() applied default states to widgets.
    # 4. manager.is_touched is False.
    # The fixture is ready.

    logging.info("Initial load complete, window ready.")
    return window


def test_example_app_basic_flow(
    qtbot: QtBot, example_window: MyWindow, example_manager: SettingsManager, caplog
):
    """Tests basic save, load, touched state, and custom data in the example app."""
    manager = example_manager
    window = example_window

    logging.info("--- Test: Initial State ---")
    # --- Initial State ---
    assert not manager.is_touched
    assert window.status_label.text() == "Status: Untouched"
    assert not window.my_checkbox.isChecked()
    # Ensure the initial display reflects the empty file state
    assert "does not exist yet" in window.settings_file_display.toPlainText()

    # --- Change Tracked Widget ---
    window.my_checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.my_checkbox.isChecked(), timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: manager.is_touched, timeout=WAIT_TIMEOUT)
    assert window.status_label.text() == "Status: *TOUCHED*"

    # --- Change Untracked Widget (should not affect touched state) ---
    initial_touched = manager.is_touched
    window.untracked_checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.untracked_checkbox.isChecked(), timeout=WAIT_TIMEOUT)
    # Wait a short time to ensure no delayed events change touched state unexpectedly
    qtbot.wait(WAIT_INTERVAL)
    assert manager.is_touched == initial_touched  # Touched state shouldn't change
    assert (
        window.status_label.text() == "Status: *TOUCHED*"
    )  # Still touched from my_checkbox

    caplog.clear()
    # Use waitSignal to block until the settings file display is updated after save
    with qtbot.waitSignal(
        window.settings_file_display_updated, timeout=WAIT_TIMEOUT
    ) as blocker:
        qtbot.mouseClick(window.save_button, Qt.MouseButton.LeftButton)

    assert not manager.is_touched
    qtbot.waitUntil(
        lambda: window.status_label.text() == "Status: Untouched", timeout=WAIT_TIMEOUT
    )
    assert "Saving settings..." in caplog.text
    # Check file content display update
    # Use waitUntil here as well, just in case the setPlainText is delayed
    qtbot.waitUntil(
        lambda: "featureCheckbox=true" in window.settings_file_display.toPlainText(),
        timeout=WAIT_TIMEOUT,
    )
    logging.info("Save Settings complete and display updated.")

    logging.info("--- Test: Verify No Unsaved Changes After Save ---")
    # --- Verify No Unsaved Changes After Save ---
    caplog.clear()
    qtbot.mouseClick(window.check_changes_button, Qt.MouseButton.LeftButton)
    qtbot.wait(WAIT_INTERVAL)  # Wait for logging
    assert "Has unsaved changes? False" in caplog.text

    logging.info("--- Test: Change Again and Load ---")
    # --- Change Again and Load ---
    window.my_checkbox.setChecked(False)
    qtbot.waitUntil(lambda: not window.my_checkbox.isChecked(), timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: manager.is_touched, timeout=WAIT_TIMEOUT)
    assert window.status_label.text() == "Status: *TOUCHED*"

    # Click load and wait for both the touched state and the checkbox state to revert
    qtbot.mouseClick(window.load_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not manager.is_touched, timeout=WAIT_TIMEOUT)

    qtbot.waitUntil(lambda: window.my_checkbox.isChecked(), timeout=WAIT_TIMEOUT)
    assert window.status_label.text() == "Status: Untouched"
    logging.info("Load Settings complete.")

    logging.info("--- Test: Custom Data ---")

    test_key = "test_example_key"
    test_value = "hello from test"
    window.custom_key_input.setText(test_key)
    window.custom_value_input.setText(test_value)
    qtbot.wait(WAIT_INTERVAL)

    logging.info("--- Test: Save custom data ---")

    qtbot.mouseClick(window.save_custom_button, Qt.MouseButton.LeftButton)

    qtbot.wait(WAIT_INTERVAL)
    assert not manager.is_touched
    logging.info("Save custom clicked.")

    qtbot.wait(WAIT_INTERVAL)
    saved_custom = manager.load_custom_data(test_key, str)
    assert saved_custom == test_value
    logging.info(f"Verified custom data saved via load_custom_data: '{saved_custom}'")

    logging.info("--- Test: Load custom data ---")

    window.custom_value_input.setText("")
    window.custom_data_display.setText("Cleared")
    qtbot.wait(WAIT_INTERVAL)

    qtbot.mouseClick(window.load_custom_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: window.custom_value_input.text() == test_value, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: f"Loaded Custom Data ('{test_key}'): {test_value}"
        in window.custom_data_display.text(),
        timeout=WAIT_TIMEOUT,
    )
    assert not manager.is_touched
    logging.info("Load custom clicked and UI updated.")

    qtbot.mouseClick(window.show_log_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.log_window.isVisible(), timeout=WAIT_TIMEOUT)
    assert window.log_window.isVisible()
    qtbot.mouseClick(
        window.log_window.button_box.button(QDialogButtonBox.StandardButton.Close),
        Qt.MouseButton.LeftButton,
    )
    qtbot.waitUntil(lambda: not window.log_window.isVisible(), timeout=WAIT_TIMEOUT)

    window.close()
