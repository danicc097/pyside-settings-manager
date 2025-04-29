# test_settings.py
from enum import Enum, auto
import os
import sys
from unittest.mock import MagicMock, patch
import pytest
from typing import Generator, Dict, Any, cast
from pathlib import Path
import logging  # Added for logging checks if needed

from PySide6.QtCore import (
    QByteArray,
    Qt,
    QSettings,
    QSize,
    Signal,
    SignalInstance,
    QTimer,
)
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QMainWindow,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QTabWidget,
    QSlider,
    QRadioButton,
    QDoubleSpinBox,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtTest import QSignalSpy

from pytestqt.qtbot import QtBot  # type: ignore

# Assume settings.py is in a package named 'pyside_settings_manager'
# Adjust the import path if your structure is different
from pyside_settings_manager.settings import (
    SETTINGS_PROPERTY,
    create_settings_manager,
    QtSettingsManager,
    SettingsHandler,  # Import the new protocol
    SettingsManager,  # Import the manager protocol
    DefaultCheckBoxHandler,  # Example handler for custom registration test
)

# Configure logging for tests if desired
# logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication instance exists for the test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def test_settings_file(tmp_path: Path) -> str:
    """Provides a temporary file path for settings."""
    fpath = tmp_path / "test_app_settings_refactored.ini"
    fpath_str = str(fpath)
    # Ensure file doesn't exist from previous runs
    if os.path.exists(fpath_str):
        os.remove(fpath_str)
    return fpath_str


@pytest.fixture
def settings_manager(
    test_settings_file: str,
    qapp: QApplication,  # Add qapp dependency
) -> Generator[QtSettingsManager, None, None]:
    """Fixture to create and cleanup QtSettingsManager with a temp file."""
    settings = QSettings(test_settings_file, QSettings.Format.IniFormat)
    manager = create_settings_manager(settings)
    assert isinstance(manager, QtSettingsManager)  # Ensure correct type
    yield manager  # Provide the manager to the test
    # Cleanup: clear settings and remove file
    settings.clear()
    # Explicitly delete QSettings object before trying to remove the file
    del settings
    if os.path.exists(test_settings_file):
        os.remove(test_settings_file)


class SettingsTestWindow(QMainWindow):
    """A standard window with various widgets for testing."""

    def __init__(self):
        super().__init__()
        self.setProperty(SETTINGS_PROPERTY, "TestMainWindow")
        self.resize(500, 400)  # Initial size

        central = QWidget()
        central.setProperty(SETTINGS_PROPERTY, "centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        # No need to call central.setLayout(layout) - QVBoxLayout(central) does this

        # --- Add widgets to layout ---

        self.checkbox_no_property = QCheckBox("Test Checkbox No Property")
        layout.addWidget(self.checkbox_no_property)

        self.checkbox = QCheckBox("Test Checkbox")
        self.checkbox.setProperty(SETTINGS_PROPERTY, "testCheckbox")
        layout.addWidget(self.checkbox)

        self.line_edit = QLineEdit("Initial Text")
        self.line_edit.setProperty(SETTINGS_PROPERTY, "testLineEdit")
        layout.addWidget(self.line_edit)

        self.push_button = QPushButton("Test Button (Checkable)")
        self.push_button.setProperty(SETTINGS_PROPERTY, "testPushButton")
        self.push_button.setCheckable(True)
        layout.addWidget(self.push_button)

        self.combo_box = QComboBox()
        self.combo_box.setProperty(SETTINGS_PROPERTY, "testComboBox")
        self.combo_box.addItems(["Option 1", "Option 2", "Option 3"])
        layout.addWidget(self.combo_box)

        self.spin_box = QSpinBox()
        self.spin_box.setProperty(SETTINGS_PROPERTY, "testSpinBox")
        self.spin_box.setRange(0, 100)
        self.spin_box.setValue(10)
        layout.addWidget(self.spin_box)

        self.double_spin_box = QDoubleSpinBox()
        self.double_spin_box.setProperty(SETTINGS_PROPERTY, "testDoubleSpinBox")
        self.double_spin_box.setRange(0.0, 10.0)
        self.double_spin_box.setValue(1.23)
        layout.addWidget(self.double_spin_box)

        # --- Radio Buttons ---
        self.radio_button1 = QRadioButton("Radio 1")
        self.radio_button1.setProperty(SETTINGS_PROPERTY, "testRadioButton1")
        self.radio_button2 = QRadioButton("Radio 2")
        self.radio_button2.setProperty(SETTINGS_PROPERTY, "testRadioButton2")
        self.radio_button1.setChecked(True)  # Start with one checked
        # GroupBox for radio buttons (itself not handled, but children are)
        radio_group = QGroupBox("Radio Group")
        radio_group.setProperty(
            SETTINGS_PROPERTY, "radioGroup"
        )  # Give groupbox a name too
        radio_layout = QVBoxLayout(radio_group)
        radio_layout.addWidget(self.radio_button1)
        radio_layout.addWidget(self.radio_button2)
        layout.addWidget(radio_group)  # Add groupbox to main layout

        # --- Other Widgets ---
        self.text_edit = QTextEdit("Initial multi-line\ntext.")
        self.text_edit.setProperty(SETTINGS_PROPERTY, "testTextEdit")
        layout.addWidget(self.text_edit)

        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty(SETTINGS_PROPERTY, "testTabWidget")
        self.tab_widget.addTab(QWidget(), "Tab 1")
        self.tab_widget.addTab(QWidget(), "Tab 2")
        layout.addWidget(self.tab_widget)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setProperty(SETTINGS_PROPERTY, "testSlider")
        self.slider.setRange(0, 50)
        self.slider.setValue(25)
        layout.addWidget(self.slider)

        # Widget to test skipping
        self.ignored_checkbox = QCheckBox("Ignored Checkbox")
        self.ignored_checkbox.setProperty(SETTINGS_PROPERTY, "ignoredCheckbox")
        layout.addWidget(self.ignored_checkbox)

        # Widget without object name (should be skipped automatically)
        self.no_name_checkbox = QCheckBox("No Name Checkbox")
        # self.no_name_checkbox has no property set
        layout.addWidget(self.no_name_checkbox)


# --- Basic Save/Load Tests (Regression Check) ---


def test_save_load_main_window(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test saving and loading QMainWindow geometry and state."""
    # if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    #     pytest.skip("Skipping main window geometry test in offscreen environment")

    main_window = SettingsTestWindow()  # Use the test window
    qtbot.add_widget(main_window)
    initial_size = QSize(700, 550)
    main_window.resize(initial_size)
    main_window.show()
    qtbot.waitExposed(main_window)

    # Initial load (should apply defaults or nothing if file empty)
    settings_manager.load_state()
    assert not settings_manager.is_touched  # Should be untouched after load

    # Save initial state
    settings_manager.save_state()
    assert not settings_manager.is_touched  # Should be untouched after save

    # Change state
    new_size = QSize(640, 480)
    main_window.resize(new_size)
    qtbot.wait(50)  # Allow event processing

    # Save changed state
    settings_manager.save_state()

    main_window.resize(300, 200)
    qtbot.wait(50)

    # Load the saved state (should restore new_size)
    settings_manager.load_state()
    qtbot.wait(50)  # Allow resize events

    assert main_window.size() == new_size
    assert not settings_manager.is_touched  # Should be untouched after load
    main_window.close()


def test_checkbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Load initial defaults

    assert not window.checkbox_no_property.isChecked()
    window.checkbox_no_property.setChecked(True)
    window.checkbox.setChecked(True)

    settings_manager.save_state()

    window.checkbox_no_property.setChecked(False)  # Change before reload
    window.checkbox.setChecked(False)  # Change before reload
    settings_manager.load_state()

    assert window.checkbox.isChecked() is True
    assert window.checkbox_no_property.isChecked() is False  # must skip without prop
    assert not settings_manager.is_touched
    window.close()


def test_lineedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_text = "Saved Text Content"
    window.line_edit.setText(test_text)
    settings_manager.save_state()
    window.line_edit.setText("Temporary Text")
    settings_manager.load_state()
    assert window.line_edit.text() == test_text
    assert not settings_manager.is_touched
    window.close()


def test_pushbutton_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    window.push_button.setChecked(True)
    settings_manager.save_state()
    window.push_button.setChecked(False)
    settings_manager.load_state()
    assert window.push_button.isChecked() is True
    assert not settings_manager.is_touched
    window.close()


def test_combobox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_index = 2
    window.combo_box.setCurrentIndex(test_index)
    settings_manager.save_state()
    window.combo_box.setCurrentIndex(0)
    settings_manager.load_state()
    assert window.combo_box.currentIndex() == test_index
    assert not settings_manager.is_touched
    window.close()


def test_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_value = 42
    window.spin_box.setValue(test_value)
    settings_manager.save_state()
    window.spin_box.setValue(0)
    settings_manager.load_state()
    assert window.spin_box.value() == test_value
    assert not settings_manager.is_touched
    window.close()


def test_double_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_value = 3.14
    window.double_spin_box.setValue(test_value)
    settings_manager.save_state()
    window.double_spin_box.setValue(0.0)
    settings_manager.load_state()
    # Use tolerance for float comparison
    assert abs(window.double_spin_box.value() - test_value) < 1e-6
    assert not settings_manager.is_touched
    window.close()


def test_radio_button_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Load initial (radio1 checked)

    # Change selection
    window.radio_button2.setChecked(True)
    assert window.radio_button2.isChecked()
    assert not window.radio_button1.isChecked()
    settings_manager.save_state()  # Save with radio2 checked

    # Change back temporarily
    window.radio_button1.setChecked(True)
    settings_manager.load_state()  # Load saved state (radio2 should be checked)

    assert window.radio_button2.isChecked() is True
    assert window.radio_button1.isChecked() is False
    assert not settings_manager.is_touched
    window.close()


def test_textedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_text = "Saved multi-line\ntext content."
    window.text_edit.setPlainText(test_text)
    settings_manager.save_state()
    window.text_edit.setPlainText("Temporary")
    settings_manager.load_state()
    assert window.text_edit.toPlainText() == test_text
    assert not settings_manager.is_touched
    window.close()


def test_tabwidget_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_index = 1
    window.tab_widget.setCurrentIndex(test_index)
    settings_manager.save_state()
    window.tab_widget.setCurrentIndex(0)
    settings_manager.load_state()
    assert window.tab_widget.currentIndex() == test_index
    assert not settings_manager.is_touched
    window.close()


def test_slider_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_value = 33
    window.slider.setValue(test_value)
    settings_manager.save_state()
    window.slider.setValue(0)
    settings_manager.load_state()
    assert window.slider.value() == test_value
    assert not settings_manager.is_touched
    window.close()


# --- Touched State Tests (Formerly Dirty State) ---


def test_initial_state_is_untouched(settings_manager: QtSettingsManager):
    """Verify the manager starts in an untouched state."""
    assert not settings_manager.is_touched


def test_load_state_makes_untouched(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Verify load_state resets the touched flag and emits the signal."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.mark_touched()  # Manually set to touched
    assert settings_manager.is_touched

    spy = QSignalSpy(settings_manager.touched_changed)
    assert spy.isValid()

    settings_manager.load_state()

    spy.wait(100)  # Wait up to 100ms

    assert not settings_manager.is_touched
    assert spy.count() == 1, f"Expected 1 signal, got {spy.count()}: {spy}"
    assert spy.at(0) == [False]  # Signal should emit False (untouched)
    window.close()


def test_save_state_makes_untouched(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Verify save_state resets the touched flag and emits the signal."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Start clean

    spy_touch = QSignalSpy(settings_manager.touched_changed)
    window.checkbox.setChecked(not window.checkbox.isChecked())  # Make a change
    spy_touch.wait(100)  # Wait for the touched signal

    assert settings_manager.is_touched
    assert spy_touch.count() >= 1  # Should have received at least one True signal

    # Now spy on the signal during save
    spy_save = QSignalSpy(settings_manager.touched_changed)
    settings_manager.save_state()
    spy_save.wait(100)  # Wait for the untouched signal

    assert not settings_manager.is_touched
    assert spy_save.count() == 1, (
        f"Expected 1 signal during save, got {spy_save.count()}: {spy_save}"
    )
    assert spy_save.at(0) == [False]  # Signal should emit False (untouched)
    window.close()


def test_widget_change_marks_touched(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Verify changing a monitored widget sets the touched flag and emits the signal."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()  # Connects signals, marks untouched
    assert not settings_manager.is_touched

    spy = QSignalSpy(settings_manager.touched_changed)
    assert spy.isValid()

    window.checkbox.setChecked(True)
    spy.wait(100)

    assert settings_manager.is_touched
    assert spy.count() == 1, f"Expected 1 signal, got {spy.count()}: {spy}"
    assert spy.at(0) == [True]  # Should emit True

    # Further changes should not emit the signal again if already touched
    signals_received = spy.count()
    window.line_edit.setText("New Text")
    qtbot.wait(50)  # Allow signal processing time
    assert spy.count() == signals_received

    window.slider.setValue(window.slider.value() + 10)
    qtbot.wait(50)
    assert spy.count() == signals_received

    assert settings_manager.is_touched
    window.close()


def test_save_custom_data_marks_touched(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify saving custom data marks the state as touched."""
    settings_manager.load_state()
    assert not settings_manager.is_touched

    class SettingsKey(str, Enum):
        def _generate_next_value_(name, start, count, last_values):  # type: ignore
            return name

        NEW_KEY = auto()

    spy = QSignalSpy(settings_manager.touched_changed)
    settings_manager.save_custom_data("custom_key", {"value": 1})
    settings_manager.save_custom_data(SettingsKey.NEW_KEY, {"test": ["123"]})
    spy.wait(100)

    assert settings_manager.is_touched
    # should have emitted just once
    assert spy.count() == 1, f"Expected 1 signals, got {spy.count()}: {spy}"
    assert spy.at(0) == [True]

    spy = QSignalSpy(settings_manager.touched_changed)
    new_key = settings_manager.load_custom_data(SettingsKey.NEW_KEY)
    assert new_key == {"test": ["123"]}
    assert spy.count() == 0  # No signal should be emitted retrieving custom data


def test_skip_widget_prevents_save_load(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify skipped widgets are not saved or loaded."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.line_edit)
    settings_manager.load_state()

    window.line_edit.setText("This should NOT be saved")
    window.checkbox.setChecked(True)  # This should be saved

    settings_manager.save_state()

    window.line_edit.setText("Reset value")
    window.checkbox.setChecked(False)

    settings_manager.load_state()

    assert window.line_edit.text() == "Reset value", (
        "Skipped widget did not retain its value"
    )
    assert window.checkbox.isChecked() is True

    window.close()


def test_skip_widget_prevents_touched(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify changes to skipped widgets do not mark state as touched."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.checkbox)
    settings_manager.load_state()

    assert not settings_manager.is_touched
    spy = QSignalSpy(settings_manager.touched_changed)

    window.checkbox.setChecked(True)
    qtbot.wait(100)

    assert not settings_manager.is_touched
    assert spy.count() == 0

    window.line_edit.setText("Change")
    spy.wait(100)

    assert settings_manager.is_touched
    assert spy.count() == 1
    assert spy.at(0) == [True]

    window.close()


def test_widget_without_property_is_skipped(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify widgets without object names are automatically skipped."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Connect signals, mark untouched

    assert not settings_manager.is_touched
    spy = QSignalSpy(settings_manager.touched_changed)

    # Change the checkbox without an object name
    initial_state = window.no_name_checkbox.isChecked()
    window.no_name_checkbox.setChecked(not initial_state)
    qtbot.wait(100)  # Allow signal processing time

    # State should remain untouched, no signal emitted
    assert not settings_manager.is_touched
    assert spy.count() == 0

    # Also check save/load doesn't affect it (implicitly tested by lack of handler)
    settings_manager.save_state()
    window.no_name_checkbox.setChecked(initial_state)  # Change it back
    settings_manager.load_state()
    assert (
        window.no_name_checkbox.isChecked() == initial_state
    )  # Should not have loaded anything

    window.close()


def test_unskip_widget_restores_management(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test that unskipping a widget makes it managed again."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Skip, load, change, save
    settings_manager.skip_widget(window.checkbox)
    settings_manager.load_state()
    window.checkbox.setChecked(True)  # This change won't be saved
    settings_manager.save_state()
    assert not settings_manager.is_touched

    # Unskip the widget
    settings_manager.unskip_widget(window.checkbox)

    # Check if signals are now connected (causes touched state)
    spy_touch = QSignalSpy(settings_manager.touched_changed)
    window.checkbox.setChecked(False)  # Change it again
    spy_touch.wait(100)
    assert settings_manager.is_touched, "Changing unskipped widget should mark touched"
    assert spy_touch.count() == 1
    assert spy_touch.at(0) == [True]

    # Save the new state (False)
    settings_manager.save_state()
    assert not settings_manager.is_touched

    # Change temporarily and reload
    window.checkbox.setChecked(True)
    settings_manager.load_state()

    # Should load the saved state (False)
    assert window.checkbox.isChecked() is False
    assert not settings_manager.is_touched

    window.close()


# --- has_unsaved_changes Tests ---


def test_has_unsaved_changes_initial(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test has_unsaved_changes returns False initially and after load."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Before load (settings file might be empty or non-existent)
    # Comparison might be against defaults, depends on QSettings behavior
    # Let's save a default state first to be sure
    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes(), (
        "Should be False after initial save"
    )

    # After load
    settings_manager.load_state()
    assert not settings_manager.has_unsaved_changes(), "Should be False after load"
    window.close()


def test_has_unsaved_changes_after_change(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes returns True after a widget change."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Load initial state
    settings_manager.save_state()  # Save it so comparison baseline is set
    assert not settings_manager.has_unsaved_changes()

    window.line_edit.setText("A new value that differs")
    qtbot.wait(50)  # Allow event processing

    assert settings_manager.has_unsaved_changes(), "Should be True after change"
    window.close()


def test_has_unsaved_changes_after_save(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes returns False after saving changes."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    settings_manager.save_state()  # Baseline

    window.spin_box.setValue(window.spin_box.value() + 5)
    assert settings_manager.has_unsaved_changes(), "Should be True after change"

    # Save the changes
    settings_manager.save_state()

    # Now it should be False again
    assert not settings_manager.has_unsaved_changes(), (
        "Should be False after saving changes"
    )
    window.close()


def test_has_unsaved_changes_ignores_skipped(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes ignores changes in skipped widgets."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    settings_manager.save_state()  # Baseline

    # Skip a widget
    settings_manager.skip_widget(window.checkbox)

    # Change the skipped widget
    window.checkbox.setChecked(not window.checkbox.isChecked())

    # Should still return False as the only change is in a skipped widget
    assert not settings_manager.has_unsaved_changes(), (
        "Changes in skipped widgets should be ignored"
    )

    window.line_edit.setText("Managed change")
    assert settings_manager.has_unsaved_changes(), (
        "Changes in managed widgets should be detected"
    )

    window.close()


def test_has_unsaved_changes_ignores_no_name(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes ignores changes in widgets without object names."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    settings_manager.save_state()  # Baseline

    # Change the widget without an object name
    window.no_name_checkbox.setChecked(not window.no_name_checkbox.isChecked())

    # Should return False as this widget is implicitly skipped
    assert not settings_manager.has_unsaved_changes(), (
        "Changes in no-name widgets should be ignored"
    )
    window.close()


def test_has_unsaved_changes_custom_data(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes does NOT detect changes only in custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    settings_manager.save_state()  # Baseline for widgets and custom data

    assert not settings_manager.has_unsaved_changes()
    assert not settings_manager.is_touched

    # Save some custom data - this marks state as touched
    settings_manager.save_custom_data("my_custom", [1, 2, 3])
    assert settings_manager.is_touched, "Saving custom data should mark touched"

    # However, has_unsaved_changes should still be False as no *widget* state changed
    assert not settings_manager.has_unsaved_changes(), (
        "has_unsaved_changes should ignore custom data changes"
    )

    # Now change a widget
    window.slider.setValue(window.slider.value() - 1)
    assert settings_manager.has_unsaved_changes(), (
        "Widget change should now be detected"
    )

    window.close()


def test_has_unsaved_changes_with_file_source(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    """Test comparing against a specific settings file."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # 1. Save initial state to the manager's default file
    settings_manager.load_state()  # Load defaults first
    window.checkbox.setChecked(False)
    window.line_edit.setText("State A")
    settings_manager.save_state()
    default_file = settings_manager._settings.fileName()

    # 2. Create a second state and save to a different file
    alt_file = str(tmp_path / "alt_settings.ini")
    window.checkbox.setChecked(True)  # Different state
    window.line_edit.setText("State B")
    settings_manager.save_to_file(alt_file)  # Saves current state (B) to alt_file

    # 3. Current state is State B. Compare against default file (State A)
    assert settings_manager.has_unsaved_changes(source=default_file), (
        "Current state (B) should differ from default file (A)"
    )

    # 4. Compare current state (B) against the alt file (State B)
    assert not settings_manager.has_unsaved_changes(source=alt_file), (
        "Current state (B) should match alt file (B)"
    )

    # 5. Load State A back into the window
    settings_manager.load_state()  # Loads from default file (State A)
    assert window.line_edit.text() == "State A"

    # 6. Compare current state (A) against alt file (State B)
    assert settings_manager.has_unsaved_changes(source=alt_file), (
        "Current state (A) should differ from alt file (B)"
    )

    window.close()


# --- Other Tests ---


def test_get_managed_widgets(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test retrieving the list of managed widgets."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Skip one widget, one has no name
    settings_manager.skip_widget(window.ignored_checkbox)
    settings_manager.load_state()  # Trigger widget discovery

    managed = settings_manager.get_managed_widgets()
    managed_names = {w.property(SETTINGS_PROPERTY) for w in managed}

    # Check that standard widgets are present
    assert window.checkbox.property(SETTINGS_PROPERTY) in managed_names
    assert window.line_edit.property(SETTINGS_PROPERTY) in managed_names
    assert window.push_button.property(SETTINGS_PROPERTY) in managed_names
    assert window.combo_box.property(SETTINGS_PROPERTY) in managed_names
    assert window.spin_box.property(SETTINGS_PROPERTY) in managed_names
    assert window.double_spin_box.property(SETTINGS_PROPERTY) in managed_names
    assert (
        window.radio_button1.property(SETTINGS_PROPERTY) in managed_names
    )  # Radio buttons included
    assert window.radio_button2.property(SETTINGS_PROPERTY) in managed_names
    assert window.text_edit.property(SETTINGS_PROPERTY) in managed_names
    assert window.tab_widget.property(SETTINGS_PROPERTY) in managed_names
    assert window.slider.property(SETTINGS_PROPERTY) in managed_names
    assert window.property(SETTINGS_PROPERTY) in managed_names  # Main window itself

    # Check that skipped/no-name widgets are absent
    assert window.ignored_checkbox.property(SETTINGS_PROPERTY) not in managed_names
    assert window.no_name_checkbox.property(SETTINGS_PROPERTY) is None  # Has no name
    assert window.no_name_checkbox not in managed  # Should not be in the list

    # Check count (adjust if SettingsTestWindow changes significantly)
    # Expected: window + checkbox + lineedit + pushbutton + combobox + spinbox + dspinbox + radio1 + radio2 + textedit + tabwidget + slider = 12
    # Note: GroupBox itself doesn't have a default handler, so it's not "managed" directly, but its children are traversed.
    assert len(managed) == 12, (
        f"Expected 12 managed widgets, found {len(managed)}: {[w.property(SETTINGS_PROPERTY) for w in managed]}"
    )

    window.close()


def test_custom_handler_registration(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test registering and using a custom handler."""

    # Use QCheckBox but with a custom handler that inverts the logic
    class InvertedCheckBoxHandler(SettingsHandler):
        def save(self, widget: QCheckBox, settings: QSettings):
            settings.setValue(
                widget.property(SETTINGS_PROPERTY), not widget.isChecked()
            )  # Inverted save

        def load(self, widget: QCheckBox, settings: QSettings):
            # Load inverted value, default to NOT current state if missing
            value = cast(
                bool,
                settings.value(
                    widget.property(SETTINGS_PROPERTY),
                    not widget.isChecked(),
                    type=bool,
                ),
            )
            widget.setChecked(not value)  # Inverted load

        def compare(self, widget: QCheckBox, settings: QSettings) -> bool:
            current_state = widget.isChecked()
            saved_inverted_state = cast(
                bool,
                settings.value(
                    widget.property(SETTINGS_PROPERTY), not current_state, type=bool
                ),
            )
            return (
                current_state == saved_inverted_state
            )  # Compare current to non-inverted saved state

        def get_signals_to_monitor(self, widget: QCheckBox) -> list[SignalInstance]:
            return [widget.stateChanged]

    # Register the custom handler for QCheckBox
    settings_manager.register_handler(QCheckBox, InvertedCheckBoxHandler())

    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Load initial state (using inverted handler)

    # Set checkbox to True, handler should save False
    window.checkbox.setChecked(True)
    settings_manager.save_state()

    # Set checkbox to False temporarily
    window.checkbox.setChecked(False)

    # Load state - handler should load False, then invert to set True
    settings_manager.load_state()

    assert window.checkbox.isChecked() is True, "Custom handler load failed"

    # Test compare: Current is True. Saved is False. Compare should return False (match after inversion)
    assert not settings_manager.has_unsaved_changes(), (
        "Custom handler compare failed (should match)"
    )

    # Change state: Current is False. Saved is False. Compare should return True (differ after inversion)
    window.checkbox.setChecked(False)
    assert settings_manager.has_unsaved_changes(), (
        "Custom handler compare failed (should differ)"
    )

    window.close()


def test_pushbutton_non_checkable_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test compare method for non-checkable push buttons returns False."""
    window = QMainWindow()
    qtbot.add_widget(window)
    button = QPushButton("Non Checkable")
    button.setProperty(SETTINGS_PROPERTY, "nonCheckableButton")
    button.setCheckable(False)
    window.setCentralWidget(button)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()
    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes()
    window.close()


def test_combobox_editable_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test save/load/compare for an editable QComboBox."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    combo = window.combo_box
    combo.setEditable(True)
    settings_manager.load_state()  # Connects signals, including currentTextChanged

    initial_text = "Initial Editable Text"
    initial_index = 0
    combo.setCurrentText(initial_text)
    combo.setCurrentIndex(initial_index)

    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes()

    # Change text only
    new_text = "Edited Text"
    combo.lineEdit().setText(
        new_text
    )  # Setting text on editable combo updates lineEdit
    QApplication.processEvents()
    assert settings_manager.has_unsaved_changes(), (
        "Change in editable text should be detected"
    )

    # Save new text state
    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes()

    # Change back temporarily
    combo.setCurrentText("Temporary Text")
    combo.setCurrentIndex(1)

    # Load saved state
    settings_manager.load_state()

    assert combo.currentText() == new_text
    assert combo.currentIndex() == initial_index  # Index wasn't saved with text change
    assert not settings_manager.is_touched
    window.close()


def test_combobox_load_invalid_index(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test loading QComboBox state with an invalid saved index defaults to 0."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Save a valid state first
    window.combo_box.setCurrentIndex(1)
    settings_manager.save_state()

    # Manually write an invalid index to the settings
    settings_manager._settings.setValue(
        f"{window.combo_box.property(SETTINGS_PROPERTY)}/currentIndex", 999
    )
    settings_manager._settings.sync()
    settings_manager.load_state()
    assert window.combo_box.currentIndex() == 0  # Should default to 0
    window.close()


def test_radio_button_compare_unsaved_checked(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test compare for radio button when its state wasn't saved and it's checked."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    radio1_key = window.radio_button1.property(SETTINGS_PROPERTY)
    radio2_key = window.radio_button2.property(SETTINGS_PROPERTY)

    # --- Step 1: Save initial state (r1=T, r2=F) ---
    settings_manager.load_state()
    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes()
    assert settings_manager._settings.value(radio1_key, type=bool) is True
    assert settings_manager._settings.value(radio2_key, type=bool) is False

    # --- Step 2: Change UI (r1=F, r2=T) and save ---
    window.radio_button2.setChecked(True)
    qtbot.wait(50)
    settings_manager.save_state()  # Saved: r1=F, r2=T
    assert not settings_manager.has_unsaved_changes()
    assert settings_manager._settings.value(radio1_key, type=bool) is False
    assert settings_manager._settings.value(radio2_key, type=bool) is True

    # --- Step 3: Change UI back (r1=T, r2=F) and compare ---
    window.radio_button1.setChecked(True)  # r2 becomes F automatically
    qtbot.wait(50)
    # Current UI: r1=T, r2=F
    # Saved state: r1=F, r2=T
    # Comparison should find differences in BOTH r1 and r2
    assert settings_manager.has_unsaved_changes(), (
        "Should detect difference: UI(r1=T, r2=F) vs Saved(r1=F, r2=T)"
    )

    # --- Step 4: Make UI match saved state again (r1=F, r2=T) ---
    window.radio_button2.setChecked(True)
    qtbot.wait(50)
    assert not settings_manager.has_unsaved_changes(), (
        "Should match saved state again after re-checking radio2"
    )

    window.close()


def test_slider_load_out_of_range(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test loading a slider value outside its range defaults to current."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    slider = window.slider  # Range 0-50, Default 25
    initial_value = slider.value()
    assert initial_value == 25

    settings_manager.load_state()  # Ensure slider is managed

    # Manually save an out-of-range value
    settings_manager._settings.setValue(slider.property(SETTINGS_PROPERTY), 100)
    settings_manager._settings.sync()

    settings_manager.load_state()
    assert slider.value() == initial_value  # Should remain unchanged
    assert "Loaded value 100 for slider testSlider is out of range" in caplog.text
    window.close()


def test_main_window_geometry_change_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes detects only geometry changes."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()
    settings_manager.save_state()
    assert not settings_manager.has_unsaved_changes()

    window.resize(window.width() + 50, window.height() - 20)
    qtbot.wait(50)  # Allow resize event
    assert settings_manager.has_unsaved_changes(), "Geometry change should be detected"
    window.close()


def test_has_unsaved_changes_with_qsettings_source(
    qtbot: QtBot, settings_manager: QtSettingsManager, test_settings_file: str
):
    """Test comparing against a specific QSettings object."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()
    window.line_edit.setText("State A")
    settings_manager.save_state()  # Save State A to default QSettings

    # Create a separate QSettings object representing a different state
    alt_settings_path = test_settings_file + ".alt"
    if os.path.exists(alt_settings_path):
        os.remove(alt_settings_path)  # Ensure clean state
    alt_settings = QSettings(alt_settings_path, QSettings.Format.IniFormat)
    alt_settings.setValue(window.line_edit.property(SETTINGS_PROPERTY), "State B")
    alt_settings.sync()

    assert settings_manager.has_unsaved_changes(source=alt_settings)
    window.close()
    # Clean up alt file
    del alt_settings
    if os.path.exists(alt_settings_path):
        os.remove(alt_settings_path)


def test_load_from_invalid_file(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test load_from_file with a non-existent or invalid file."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    initial_text = window.line_edit.text()
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()  # Initial load/connect
    settings_manager.mark_touched()  # Mark dirty to check if it resets
    assert settings_manager.is_touched

    invalid_path = "non_existent_or_invalid_settings_file.ini"
    # Ensure file doesn't exist
    if os.path.exists(invalid_path):
        os.remove(invalid_path)

    settings_manager.load_from_file(invalid_path)

    # Check that the warning IS logged because load_from_file checks status
    # Note: QSettings might return NoError for a non-existent file, but the
    # test should still pass as state remains unchanged and touched is reset.
    # If the file *was* corrupted, the warning MUST be present.
    # This assertion allows for both scenarios gracefully.
    assert (
        f"Could not load settings from {invalid_path}" in caplog.text
        or settings_manager._settings.status() == QSettings.Status.NoError
    )

    assert window.line_edit.text() == initial_text  # State should be unchanged
    assert not settings_manager.is_touched  # Should reset touched state
    window.close()
    # Clean up just in case a test variation creates the file
    if os.path.exists(invalid_path):
        os.remove(invalid_path)


def test_register_invalid_handler_type(settings_manager: QtSettingsManager):
    """Test registering a handler that doesn't match the protocol."""

    class InvalidHandler:
        pass

    with pytest.raises(
        TypeError, match="Handler must conform to SettingsHandler protocol"
    ):
        settings_manager.register_handler(QWidget, InvalidHandler())  # type: ignore


def test_save_unpickleable_custom_data(settings_manager: QtSettingsManager, caplog):
    """Test saving custom data that cannot be pickled."""
    unpickleable_data = lambda x: x  # Lambda functions are generally not pickleable
    key = "unpickleable"

    settings_manager.save_custom_data(key, unpickleable_data)
    # Check log for error message
    assert f"Could not pickle custom data for key '{key}'" in caplog.text
    # Check that the value wasn't actually stored (or stored as empty)
    assert settings_manager._settings.value(f"customData/{key}") is None


def test_load_custom_data_not_found(settings_manager: QtSettingsManager):
    """Test loading custom data for a key that doesn't exist."""
    assert settings_manager.load_custom_data("non_existent_key") is None


def test_load_custom_data_empty_bytes(settings_manager: QtSettingsManager, caplog):
    """Test loading custom data when settings contain empty bytes."""
    key = "empty_bytes_key"
    settings_manager._settings.setValue(f"customData/{key}", QByteArray(b""))
    settings_manager._settings.sync()

    assert settings_manager.load_custom_data(key) is None
    assert f"No valid data found for custom data key '{key}'" in caplog.text


def test_load_custom_data_unpickle_error(settings_manager: QtSettingsManager, caplog):
    """Test loading custom data that causes an UnpicklingError."""
    key = "garbage_data"
    settings_manager._settings.setValue(
        f"customData/{key}", QByteArray(b"this is not pickled data")
    )
    settings_manager._settings.sync()

    assert settings_manager.load_custom_data(key) is None
    assert f"Could not unpickle data for key '{key}'" in caplog.text


class FaultyHandler(SettingsHandler):
    """A handler designed to fail during specific operations."""

    def __init__(self, fail_on="load"):
        self.fail_on = fail_on

    def _maybe_fail(self, operation: str):
        if operation == self.fail_on:
            raise RuntimeError(f"Intentional failure during {operation}")

    def save(self, widget: QWidget, settings: QSettings):
        self._maybe_fail("save")
        settings.setValue(widget.property(SETTINGS_PROPERTY), "saved")

    def load(self, widget: QWidget, settings: QSettings):
        self._maybe_fail("load")
        # Try to modify the widget state even if failing after
        if isinstance(widget, QCheckBox):
            widget.setText("Load Attempted")

    def compare(self, widget: QWidget, settings: QSettings) -> bool:
        self._maybe_fail("compare")
        return False

    def get_signals_to_monitor(self, widget: QWidget) -> list[SignalInstance]:
        self._maybe_fail("get_signals")
        if isinstance(widget, QCheckBox):
            return [widget.stateChanged]
        return []


def test_exception_during_load(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test graceful handling of exception during widget load."""
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="load"))
    window = SettingsTestWindow()  # Has a QCheckBox key "testCheckbox"
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Save a valid state first so load has something to read
    settings_manager.save_state()

    settings_manager.load_state()  # Should trigger the faulty handler's load

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)

    # Check specifically for the error logged within _process_widget_and_recurse
    expected_log = f"Error during 'load' on widget '{checkbox_key}' (QCheckBox)"
    assert expected_log in caplog.text
    # The broader "Error during recursive load" from _perform_load should NOT appear
    # if the exception is caught within the recursion as expected.
    assert "Error during recursive load" not in caplog.text
    assert "Intentional failure during load" in caplog.text

    window.close()


def test_exception_during_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test graceful handling of exception during widget compare."""
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="compare"))
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    settings_manager.save_state()

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)

    # This should return True because the compare error is treated as a difference
    assert settings_manager.has_unsaved_changes()

    # Check for the actual error log format which includes the key
    expected_log = f"Error during 'compare' on widget '{checkbox_key}' (QCheckBox)"
    assert expected_log in caplog.text
    assert "Intentional failure during compare" in caplog.text
    window.close()


def test_exception_getting_signals(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test graceful handling of exception during get_signals_to_monitor."""
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="get_signals"))
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()  # Should trigger the faulty handler's get_signals during connect

    assert "Error getting signals for widget testCheckbox" in caplog.text
    assert "Intentional failure during get_signals" in caplog.text
    # Check that the signal wasn't actually connected
    spy = QSignalSpy(settings_manager.touched_changed)
    window.checkbox.setChecked(not window.checkbox.isChecked())
    qtbot.wait(50)
    assert spy.count() == 0  # Signal should not be connected, so no emission

    window.close()


def test_has_unsaved_changes_invalid_source_type(settings_manager: QtSettingsManager):
    """Test has_unsaved_changes raises TypeError for invalid source type."""
    with pytest.raises(
        TypeError, match="Source must be None, a filepath string, or a QSettings object"
    ):
        settings_manager.has_unsaved_changes(source=123)  # type: ignore


def test_connect_signals_idempotent(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test that calling _connect_signals multiple times is safe."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager._disconnect_all_widget_signals()  # Ensure clean state before first connect
    settings_manager._connect_signals(window)

    initial_connections = dict(settings_manager._connected_signals)
    initial_key_count = len(initial_connections)
    assert initial_key_count > 0

    settings_manager._connect_signals(window)  # shouldn't crash or duplicate

    final_key_count = len(settings_manager._connected_signals)

    assert final_key_count == initial_key_count, (
        f"Number of connected widgets changed: {initial_key_count} -> {final_key_count}"
    )

    # check signal count per widget didn't increase
    final_connections = dict(settings_manager._connected_signals)
    for widget, signals in initial_connections.items():
        assert widget in final_connections, (
            f"Widget {widget.property(SETTINGS_PROPERTY)} missing after second connect"
        )
        assert len(final_connections[widget]) == len(signals), (
            f"Signal count for widget {widget.property(SETTINGS_PROPERTY)} changed: {len(signals)} -> {len(final_connections[widget])}"
        )

    window.close()


# --- Test for QSettings error status during load_from_file ---
def test_load_from_file_error_status(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path, caplog
):
    """Test load_from_file when QSettings reports an error status."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    initial_text = window.line_edit.text()
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Connect signals etc.
    settings_manager.mark_touched()  # Mark dirty to check reset

    # Mock QSettings to return an error status
    mock_settings = MagicMock(spec=QSettings)
    mock_settings.status.return_value = QSettings.Status.AccessError  # Simulate error

    # Patch QSettings constructor to return our mock
    with patch(
        "pyside_settings_manager.settings.QSettings", return_value=mock_settings
    ) as mock_qsettings_ctor:
        settings_manager.load_from_file("dummy_path.ini")

    # Assertions
    mock_qsettings_ctor.assert_called_once_with(
        "dummy_path.ini", mock_qsettings_ctor.Format.IniFormat
    )
    mock_settings.status.assert_called()
    assert (
        "Could not load settings from dummy_path.ini. Status: Status.AccessError"
        in caplog.text
    )
    assert window.line_edit.text() == initial_text  # State unchanged
    assert not settings_manager.is_touched  # Touched state reset
    # Check signals were disconnected (part of the error path)
    assert not settings_manager._connected_signals

    window.close()


# --- Test for QSettings error status during has_unsaved_changes ---
def test_has_unsaved_changes_invalid_file_source(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path, caplog
):
    """Test has_unsaved_changes when source file QSettings reports an error."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()

    # Mock QSettings to return an error status
    mock_settings = MagicMock(spec=QSettings)
    mock_settings.status.return_value = QSettings.Status.FormatError  # Simulate error

    # Patch QSettings constructor
    with patch(
        "pyside_settings_manager.settings.QSettings", return_value=mock_settings
    ) as mock_qsettings_ctor:
        result = settings_manager.has_unsaved_changes(source="bad_format.ini")

    # Assertions
    mock_qsettings_ctor.assert_called_once_with(
        "bad_format.ini", mock_qsettings_ctor.Format.IniFormat
    )
    # Use assert_called() because status() is checked in the if and used in the log
    mock_settings.status.assert_called()
    assert (
        "Cannot compare: Failed to load settings from bad_format.ini. Status: Status.FormatError"
        in caplog.text
    )
    assert result is False  # Should return False on error

    window.close()


def test_connect_invalid_signal_object(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test connecting signals when handler returns an invalid object."""

    class BadSignalHandler(SettingsHandler):
        def save(self, widget: QWidget, settings: QSettings):
            pass

        def load(self, widget: QWidget, settings: QSettings):
            pass

        def compare(self, widget: QWidget, settings: QSettings) -> bool:
            return False

        def get_signals_to_monitor(self, widget: QWidget) -> list[Any]:
            # Return something that's not a SignalInstance
            return [123, "not a signal"]

    settings_manager.register_handler(QCheckBox, BadSignalHandler())
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()  # This triggers _connect_signals

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)
    assert f"Invalid signal object for {checkbox_key}: 123" in caplog.text
    assert f"Invalid signal object for {checkbox_key}: not a signal" in caplog.text
    # Ensure the widget itself is not in _connected_signals if all signals failed
    assert window.checkbox not in settings_manager._connected_signals

    window.close()
    # Unregister handler to avoid affecting other tests
    settings_manager.register_handler(QCheckBox, DefaultCheckBoxHandler())


def test_connect_signal_connect_error(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test connecting signals when the signal's connect() method raises error."""

    # Create a mock signal object that fails on connect
    mock_signal = MagicMock(spec=SignalInstance)
    mock_signal.connect.side_effect = RuntimeError("Intentional connect error")
    mock_signal.signal = "mockSignalWithError"

    class ErrorOnConnectHandler(SettingsHandler):
        def save(self, widget: QWidget, settings: QSettings):
            pass

        def load(self, widget: QWidget, settings: QSettings):
            pass

        def compare(self, widget: QWidget, settings: QSettings) -> bool:
            return False

        def get_signals_to_monitor(self, widget: QWidget) -> list[SignalInstance]:
            return [mock_signal]  # Return the faulty mock signal

    settings_manager.register_handler(QCheckBox, ErrorOnConnectHandler())
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()  # Triggers connect

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)
    assert (
        f"Failed to connect signal mockSignalWithError for {checkbox_key}: Intentional connect error"
        in caplog.text
    )
    assert window.checkbox not in settings_manager._connected_signals

    window.close()
    # Unregister handler
    settings_manager.register_handler(QCheckBox, DefaultCheckBoxHandler())


def test_disconnect_error_handling(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Attempt to test disconnect error handling."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # --- Part 1: Verify connection ---
    settings_manager.load_state()  # Connect signals

    widget_to_check = window.checkbox  # The instance the test knows
    target_property = widget_to_check.property(SETTINGS_PROPERTY)
    assert target_property == "testCheckbox"

    # Find the actual key instance used by the manager
    found_key_instance = None
    logging.info(f"--- Searching for key with property '{target_property}' ---")
    for key_widget in settings_manager._connected_signals.keys():
        key_property = key_widget.property(SETTINGS_PROPERTY)
        logging.info(
            f"Checking Key Instance ID: {id(key_widget)}, Property: {key_property}"
        )
        if key_property == target_property:
            found_key_instance = key_widget
            logging.info(f"--- Found Key Instance ID: {id(found_key_instance)} ---")
            break  # Stop after finding the first match

    # Assert that *some* instance with the correct property was found and connected
    assert found_key_instance is not None, (
        f"No widget with property '{target_property}' found as key in connected signals."
    )
    assert found_key_instance in settings_manager._connected_signals, (
        "The found key instance should be in the dictionary keys."
    )
    assert len(settings_manager._connected_signals[found_key_instance]) > 0, (
        f"No signals recorded for the found key instance '{target_property}'."
    )

    logging.info(f"Target widget instance ID used by test: {id(widget_to_check)}")
    logging.info(
        f"Successfully verified connection for widget '{target_property}' (instance {id(found_key_instance)})"
    )

    # --- Part 2: Test disconnection ---
    # Delete the widget C++ object using the instance the test holds
    widget_to_check.deleteLater()
    qtbot.wait(50)  # Allow deletion event to process
    logging.info(f"--- Deleted widget instance {id(widget_to_check)} ---")

    # Now try disconnecting all signals.
    try:
        settings_manager._disconnect_all_widget_signals()
        logging.info("--- Called _disconnect_all_widget_signals ---")
    except Exception as e:  # pragma: no cover
        pytest.fail(f"_disconnect_all_widget_signals raised unexpected exception: {e}")

    # Check the specific key instance (found earlier) is removed from the tracking dict
    assert found_key_instance not in settings_manager._connected_signals, (
        "Widget key instance should have been removed from connected signals after disconnect"
    )
    logging.info(
        f"--- Verified key instance {id(found_key_instance)} is no longer in connected signals ---"
    )

    window.close()


# --- Test for custom data pickle errors ---


class Unpickleable:  # Defined locally
    def __getstate__(self):
        raise TypeError("This object cannot be pickled")


def test_save_unpickleable_custom_data_type_error(
    settings_manager: QtSettingsManager, caplog
):
    """Test saving custom data that raises TypeError during pickling."""
    unpickleable_data = Unpickleable()
    key = "unpickleable_type_error"

    settings_manager.save_custom_data(key, unpickleable_data)
    # Check log for error message
    assert f"Could not pickle custom data for key '{key}'" in caplog.text
    assert "This object cannot be pickled" in caplog.text
    # Check that the value wasn't actually stored (or stored as empty)
    assert settings_manager._settings.value(f"customData/{key}") is None


def test_load_custom_data_invalid_bytes(settings_manager: QtSettingsManager, caplog):
    """Test loading custom data when settings contain invalid (non-pickle) bytes."""
    key = "invalid_bytes_key"
    # Save some non-empty bytes that are definitely not a valid pickle stream
    invalid_bytes = b"\x80\x04\x95\x00\x00\x00\x00\x00\x00\x00\x8c\x08INVALID."  # Example invalid pickle
    settings_manager._settings.setValue(f"customData/{key}", QByteArray(invalid_bytes))
    settings_manager._settings.sync()

    # This should trigger the pickle.loads() error path
    assert settings_manager.load_custom_data(key) is None
    # Check specifically for the unpickling error log
    assert f"Error unpickling data for key '{key}'" in caplog.text
