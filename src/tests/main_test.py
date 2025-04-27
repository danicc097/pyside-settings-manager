# test_settings.py
import os
import sys
import pytest
from typing import Generator, Dict, Any, cast
from pathlib import Path
import logging  # Added for logging checks if needed

from PySide6.QtCore import Qt, QSettings, QSize, Signal, SignalInstance, QTimer
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


class TestSettingsWindow(QMainWindow):
    """A standard window with various widgets for testing."""

    def __init__(self):
        super().__init__()
        self.setObjectName("TestMainWindow")
        self.resize(500, 400)  # Initial size

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        # No need to call central.setLayout(layout) - QVBoxLayout(central) does this

        # --- Add widgets to layout ---
        self.checkbox = QCheckBox("Test Checkbox")
        self.checkbox.setObjectName("testCheckbox")
        layout.addWidget(self.checkbox)

        self.line_edit = QLineEdit("Initial Text")
        self.line_edit.setObjectName("testLineEdit")
        layout.addWidget(self.line_edit)

        self.push_button = QPushButton("Test Button (Checkable)")
        self.push_button.setObjectName("testPushButton")
        self.push_button.setCheckable(True)
        layout.addWidget(self.push_button)

        self.combo_box = QComboBox()
        self.combo_box.setObjectName("testComboBox")
        self.combo_box.addItems(["Option 1", "Option 2", "Option 3"])
        layout.addWidget(self.combo_box)

        self.spin_box = QSpinBox()
        self.spin_box.setObjectName("testSpinBox")
        self.spin_box.setRange(0, 100)
        self.spin_box.setValue(10)
        layout.addWidget(self.spin_box)

        self.double_spin_box = QDoubleSpinBox()
        self.double_spin_box.setObjectName("testDoubleSpinBox")
        self.double_spin_box.setRange(0.0, 10.0)
        self.double_spin_box.setValue(1.23)
        layout.addWidget(self.double_spin_box)

        # --- Radio Buttons ---
        self.radio_button1 = QRadioButton("Radio 1")
        self.radio_button1.setObjectName("testRadioButton1")
        self.radio_button2 = QRadioButton("Radio 2")
        self.radio_button2.setObjectName("testRadioButton2")
        self.radio_button1.setChecked(True)  # Start with one checked
        # GroupBox for radio buttons (itself not handled, but children are)
        radio_group = QGroupBox("Radio Group")
        radio_group.setObjectName("radioGroup")  # Give groupbox a name too
        radio_layout = QVBoxLayout(radio_group)
        radio_layout.addWidget(self.radio_button1)
        radio_layout.addWidget(self.radio_button2)
        layout.addWidget(radio_group)  # Add groupbox to main layout

        # --- Other Widgets ---
        self.text_edit = QTextEdit("Initial multi-line\ntext.")
        self.text_edit.setObjectName("testTextEdit")
        layout.addWidget(self.text_edit)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("testTabWidget")
        self.tab_widget.addTab(QWidget(), "Tab 1")
        self.tab_widget.addTab(QWidget(), "Tab 2")
        layout.addWidget(self.tab_widget)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("testSlider")
        self.slider.setRange(0, 50)
        self.slider.setValue(25)
        layout.addWidget(self.slider)

        # Widget to test skipping
        self.ignored_checkbox = QCheckBox("Ignored Checkbox")
        self.ignored_checkbox.setObjectName("ignoredCheckbox")
        layout.addWidget(self.ignored_checkbox)

        # Widget without object name (should be skipped automatically)
        self.no_name_checkbox = QCheckBox("No Name Checkbox")
        # self.no_name_checkbox has no objectName set
        layout.addWidget(self.no_name_checkbox)


# --- Basic Save/Load Tests (Regression Check) ---


def test_save_load_main_window(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test saving and loading QMainWindow geometry and state."""
    # if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    #     pytest.skip("Skipping main window geometry test in offscreen environment")

    main_window = TestSettingsWindow()  # Use the test window
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
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()  # Load initial defaults

    window.checkbox.setChecked(True)
    settings_manager.save_state()

    window.checkbox.setChecked(False)  # Change before reload
    settings_manager.load_state()

    assert window.checkbox.isChecked() is True
    assert not settings_manager.is_touched
    window.close()


def test_lineedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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

    spy = QSignalSpy(settings_manager.touched_changed)
    settings_manager.save_custom_data("custom_key", {"value": 1})
    spy.wait(100)

    assert settings_manager.is_touched
    assert spy.count() == 1, f"Expected 1 signal, got {spy.count()}: {spy}"
    assert spy.at(0) == [True]

    signals_received = spy.count()
    settings_manager.save_custom_data("custom_key", {"value": 2})
    qtbot.wait(50)
    assert spy.count() == signals_received


def test_skip_widget_prevents_save_load(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify skipped widgets are not saved or loaded."""
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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


def test_widget_without_objectname_is_skipped(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify widgets without object names are automatically skipped."""
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
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
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Skip one widget, one has no name
    settings_manager.skip_widget(window.ignored_checkbox)
    settings_manager.load_state()  # Trigger widget discovery

    managed = settings_manager.get_managed_widgets()
    managed_names = {w.objectName() for w in managed}

    # Check that standard widgets are present
    assert window.checkbox.objectName() in managed_names
    assert window.line_edit.objectName() in managed_names
    assert window.push_button.objectName() in managed_names
    assert window.combo_box.objectName() in managed_names
    assert window.spin_box.objectName() in managed_names
    assert window.double_spin_box.objectName() in managed_names
    assert window.radio_button1.objectName() in managed_names  # Radio buttons included
    assert window.radio_button2.objectName() in managed_names
    assert window.text_edit.objectName() in managed_names
    assert window.tab_widget.objectName() in managed_names
    assert window.slider.objectName() in managed_names
    assert window.objectName() in managed_names  # Main window itself

    # Check that skipped/no-name widgets are absent
    assert window.ignored_checkbox.objectName() not in managed_names
    assert window.no_name_checkbox.objectName() == ""  # Has no name
    assert window.no_name_checkbox not in managed  # Should not be in the list

    # Check count (adjust if TestSettingsWindow changes significantly)
    # Expected: window + checkbox + lineedit + pushbutton + combobox + spinbox + dspinbox + radio1 + radio2 + textedit + tabwidget + slider = 12
    # Note: GroupBox itself doesn't have a default handler, so it's not "managed" directly, but its children are traversed.
    assert len(managed) == 12, (
        f"Expected 12 managed widgets, found {len(managed)}: {[w.objectName() for w in managed]}"
    )

    window.close()


def test_custom_handler_registration(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test registering and using a custom handler."""

    # Use QCheckBox but with a custom handler that inverts the logic
    class InvertedCheckBoxHandler(SettingsHandler):
        def save(self, widget: QCheckBox, settings: QSettings):
            settings.setValue(
                widget.objectName(), not widget.isChecked()
            )  # Inverted save

        def load(self, widget: QCheckBox, settings: QSettings):
            # Load inverted value, default to NOT current state if missing
            value = cast(
                bool,
                settings.value(widget.objectName(), not widget.isChecked(), type=bool),
            )
            widget.setChecked(not value)  # Inverted load

        def compare(self, widget: QCheckBox, settings: QSettings) -> bool:
            current_state = widget.isChecked()
            saved_inverted_state = cast(
                bool, settings.value(widget.objectName(), not current_state, type=bool)
            )
            return (
                current_state == saved_inverted_state
            )  # Compare current to non-inverted saved state

        def get_signals_to_monitor(self, widget: QCheckBox) -> list[SignalInstance]:
            return [widget.stateChanged]

    # Register the custom handler for QCheckBox
    settings_manager.register_handler(QCheckBox, InvertedCheckBoxHandler())

    window = TestSettingsWindow()
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
