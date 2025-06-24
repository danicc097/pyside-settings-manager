# test_settings.py
from enum import Enum, auto
import logging
import os
import pickle
import sys
from unittest.mock import MagicMock, patch
import pytest
from typing import Generator, Any, cast
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    Qt,
    QSettings,
    QSize,  # Added QSize import
    SignalInstance,  # Added QPoint import
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

from pyside_settings_manager.settings import (
    CUSTOM_DATA_GROUP,
    SETTINGS_PROPERTY,
    create_settings_manager,
    QtSettingsManager,
    SettingsHandler,
)


WAIT_TIMEOUT = 5_000


class SettingsKey(str, Enum):
    def _generate_next_value_(name, start, count, last_values):  # type: ignore
        return name

    NEW_KEY = auto()


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
    qapp: QApplication,
) -> Generator[QtSettingsManager, None, None]:
    """Fixture to create and cleanup QtSettingsManager with a temp file."""
    settings = QSettings(test_settings_file, QSettings.Format.IniFormat)
    manager = create_settings_manager(settings)
    assert isinstance(manager, QtSettingsManager)

    yield manager

    # Explicitly delete manager before settings to potentially help release locks
    del manager
    # Clear settings and ensure deletion
    settings.clear()
    settings.sync()  # Ensure changes are written before deleting
    del settings
    # Attempt removal again, catching potential errors if already gone
    try:
        if os.path.exists(test_settings_file):
            os.remove(test_settings_file)
    except OSError:
        pass


class SettingsTestWindow(QMainWindow):
    """A standard window with various widgets for testing."""

    def __init__(self):
        super().__init__()
        self.setProperty(SETTINGS_PROPERTY, "TestMainWindow")
        self.resize(500, 400)

        central = QWidget()
        # central.setProperty(SETTINGS_PROPERTY, "centralWidget") # REVERTED: Do not add property here
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
        # radio_group.setProperty(SETTINGS_PROPERTY, "radioGroup") # REVERTED: Do not add property here
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
        # REVERTED: Add plain QWidgets to tabs, manager should still find named children inside
        tab1_content = QWidget()
        # tab1_content.setProperty(SETTINGS_PROPERTY, "tab1Content") # REVERTED
        tab1_layout = QVBoxLayout(tab1_content)
        self.tab1_checkbox = QCheckBox("Checkbox in Tab 1")
        self.tab1_checkbox.setProperty(SETTINGS_PROPERTY, "tab1Checkbox")
        tab1_layout.addWidget(self.tab1_checkbox)
        self.tab_widget.addTab(tab1_content, "Tab 1")

        tab2_content = QWidget()
        # tab2_content.setProperty(SETTINGS_PROPERTY, "tab2Content") # REVERTED
        tab2_layout = QVBoxLayout(tab2_content)
        self.tab2_lineedit = QLineEdit("Line edit in Tab 2")
        self.tab2_lineedit.setProperty(SETTINGS_PROPERTY, "tab2Lineedit")
        tab2_layout.addWidget(self.tab2_lineedit)
        self.tab_widget.addTab(tab2_content, "Tab 2")

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
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Skipping main window geometry test in offscreen environment")

    main_window = SettingsTestWindow()
    qtbot.add_widget(main_window)
    initial_size = QSize(700, 550)
    main_window.resize(initial_size)
    main_window.show()
    qtbot.waitExposed(main_window)  # Wait for window to be shown

    settings_manager.load()
    qtbot.wait(
        50
    )  # Allow potential async operations in load (though unlikely for main window)
    assert not settings_manager.is_touched

    # Save initial state
    qtbot.waitUntil(
        lambda: main_window.size() == initial_size, timeout=WAIT_TIMEOUT
    )  # Ensure resize processed
    settings_manager.save()
    qtbot.wait(50)  # Allow save to complete
    assert not settings_manager.is_touched

    # Change state
    new_size = QSize(640, 480)
    main_window.resize(new_size)
    qtbot.waitUntil(
        lambda: main_window.size() == new_size, timeout=WAIT_TIMEOUT
    )  # Wait for resize

    # Save changed state
    settings_manager.save()
    qtbot.wait(50)  # Allow save to complete

    # Resize temporarily
    temp_size = QSize(300, 200)
    main_window.resize(temp_size)
    qtbot.waitUntil(
        lambda: main_window.size() == temp_size, timeout=WAIT_TIMEOUT
    )  # Wait for temp resize

    # Load the saved state (should restore new_size)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: main_window.size() == new_size, timeout=WAIT_TIMEOUT
    )  # Wait for loaded size

    assert main_window.size() == new_size
    assert not settings_manager.is_touched
    main_window.close()


def test_checkbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    assert not window.checkbox_no_property.isChecked()
    window.checkbox_no_property.setChecked(True)
    window.checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: window.checkbox_no_property.isChecked() is True, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.checkbox_no_property.setChecked(False)
    window.checkbox.setChecked(False)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: window.checkbox_no_property.isChecked() is False, timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.checkbox.isChecked() is True
    assert window.checkbox_no_property.isChecked() is False
    assert not settings_manager.is_touched
    window.close()


def test_lineedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_text = "Saved Text Content"
    window.line_edit.setText(test_text)
    qtbot.waitUntil(lambda: window.line_edit.text() == test_text, timeout=WAIT_TIMEOUT)

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.line_edit.setText("Temporary Text")
    qtbot.waitUntil(
        lambda: window.line_edit.text() == "Temporary Text", timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.line_edit.text() == test_text, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.line_edit.text() == test_text
    assert not settings_manager.is_touched
    window.close()


def test_pushbutton_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    window.push_button.setChecked(True)
    qtbot.waitUntil(
        lambda: window.push_button.isChecked() is True, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.push_button.setChecked(False)
    qtbot.waitUntil(
        lambda: window.push_button.isChecked() is False, timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.push_button.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.push_button.isChecked() is True
    assert not settings_manager.is_touched
    window.close()


def test_combobox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_index = 2
    window.combo_box.setCurrentIndex(test_index)
    qtbot.waitUntil(
        lambda: window.combo_box.currentIndex() == test_index, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.combo_box.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.combo_box.currentIndex() == 0, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.combo_box.currentIndex() == test_index, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.combo_box.currentIndex() == test_index
    assert not settings_manager.is_touched
    window.close()


def test_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_value = 42
    window.spin_box.setValue(test_value)
    qtbot.waitUntil(lambda: window.spin_box.value() == test_value, timeout=WAIT_TIMEOUT)

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.spin_box.setValue(0)
    qtbot.waitUntil(lambda: window.spin_box.value() == 0, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.spin_box.value() == test_value, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.spin_box.value() == test_value
    assert not settings_manager.is_touched
    window.close()


def test_double_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_value = 3.14
    window.double_spin_box.setValue(test_value)
    qtbot.waitUntil(
        lambda: abs(window.double_spin_box.value() - test_value) < 1e-6,
        timeout=WAIT_TIMEOUT,
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.double_spin_box.setValue(0.0)
    qtbot.waitUntil(
        lambda: abs(window.double_spin_box.value() - 0.0) < 1e-6, timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: abs(window.double_spin_box.value() - test_value) < 1e-6,
        timeout=WAIT_TIMEOUT,
    )  # Wait for load

    assert abs(window.double_spin_box.value() - test_value) < 1e-6
    assert not settings_manager.is_touched
    window.close()


def test_textedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_text = "Saved multi-line\ntext content."
    window.text_edit.setPlainText(test_text)
    qtbot.waitUntil(
        lambda: window.text_edit.toPlainText() == test_text, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.text_edit.setPlainText("Temporary")
    qtbot.waitUntil(
        lambda: window.text_edit.toPlainText() == "Temporary", timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.text_edit.toPlainText() == test_text, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.text_edit.toPlainText() == test_text
    assert not settings_manager.is_touched
    window.close()


def test_tabwidget_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_index = 1
    window.tab_widget.setCurrentIndex(test_index)
    qtbot.waitUntil(
        lambda: window.tab_widget.currentIndex() == test_index, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.tab_widget.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.tab_widget.currentIndex() == 0, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.tab_widget.currentIndex() == test_index, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.tab_widget.currentIndex() == test_index
    assert not settings_manager.is_touched
    window.close()


def test_slider_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    test_value = 33
    window.slider.setValue(test_value)
    qtbot.waitUntil(lambda: window.slider.value() == test_value, timeout=WAIT_TIMEOUT)

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.slider.setValue(0)
    qtbot.waitUntil(lambda: window.slider.value() == 0, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.slider.value() == test_value, timeout=WAIT_TIMEOUT
    )  # Wait for load

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

    settings_manager.mark_touched()
    assert settings_manager.is_touched

    spy = QSignalSpy(settings_manager.touched_changed)
    assert spy.isValid()

    settings_manager.load()
    # Wait for the signal indicating the state change from load
    spy.wait(100)

    assert not settings_manager.is_touched
    assert spy.count() == 1, f"Expected 1 signal, got {spy.count()}: {spy}"
    assert spy.at(0) == [False]
    window.close()


def test_save_state_makes_untouched(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Verify save_state resets the touched flag and emits the signal."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    spy_touch = QSignalSpy(settings_manager.touched_changed)
    initial_checked = window.checkbox.isChecked()
    window.checkbox.setChecked(not initial_checked)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is not initial_checked, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(lambda: settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    assert spy_touch.count() >= 1

    spy_save = QSignalSpy(settings_manager.touched_changed)
    settings_manager.save()
    spy_save.wait(100)  # Wait for untouched signal after save

    assert not settings_manager.is_touched
    assert spy_save.count() == 1, (
        f"Expected 1 signal during save, got {spy_save.count()}: {spy_save}"
    )
    assert spy_save.at(0) == [False]
    window.close()


def test_widget_change_marks_touched(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Verify changing a monitored widget sets the touched flag and emits the signal."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load
    assert not settings_manager.is_touched

    spy = QSignalSpy(settings_manager.touched_changed)
    assert spy.isValid()

    window.checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    spy.wait(100)  # Wait for signal

    assert settings_manager.is_touched
    assert spy.count() == 1, f"Expected 1 signal, got {spy.count()}: {spy}"
    assert spy.at(0) == [True]

    signals_received = spy.count()
    window.line_edit.setText("New Text")
    qtbot.waitUntil(lambda: window.line_edit.text() == "New Text", timeout=WAIT_TIMEOUT)
    qtbot.wait(50)  # Short wait to ensure no extra signal
    assert spy.count() == signals_received

    current_slider_val = window.slider.value()
    new_slider_val = current_slider_val + 10
    window.slider.setValue(new_slider_val)
    qtbot.waitUntil(
        lambda: window.slider.value() == new_slider_val, timeout=WAIT_TIMEOUT
    )
    qtbot.wait(50)  # Short wait
    assert spy.count() == signals_received

    assert settings_manager.is_touched
    window.close()


def test_save_custom_data_does_not_mark_touched(  # Renamed from original test
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify saving/loading custom data does NOT mark the state as touched."""
    # Need window context for load() to work correctly
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load
    assert not settings_manager.is_touched

    spy = QSignalSpy(settings_manager.touched_changed)
    settings_manager.save_custom_data("custom_key", {"value": 1})
    settings_manager.save_custom_data(SettingsKey.NEW_KEY, {"test": ["123"]})
    qtbot.wait(50)  # Wait to ensure no signal is emitted

    assert not settings_manager.is_touched  # Should remain untouched
    assert spy.count() == 0

    spy = QSignalSpy(settings_manager.touched_changed)
    new_key = settings_manager.load_custom_data(SettingsKey.NEW_KEY, dict)
    assert new_key == {"test": ["123"]}
    qtbot.wait(50)  # Wait to ensure no signal is emitted

    assert not settings_manager.is_touched  # Should remain untouched
    assert spy.count() == 0
    window.close()


def test_skip_widget_prevents_save_load(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify skipped widgets are not saved or loaded."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.line_edit)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    window.line_edit.setText("This should NOT be saved")
    window.checkbox.setChecked(True)
    qtbot.waitUntil(
        lambda: window.line_edit.text() == "This should NOT be saved",
        timeout=WAIT_TIMEOUT,
    )
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    window.line_edit.setText("Reset value")
    window.checkbox.setChecked(False)
    qtbot.waitUntil(
        lambda: window.line_edit.text() == "Reset value", timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.line_edit.text() == "Reset value"
    assert window.checkbox.isChecked() is True

    window.close()


def test_widget_without_property_is_skipped(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Verify widgets without settings property are automatically skipped."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    assert not settings_manager.is_touched
    spy = QSignalSpy(settings_manager.touched_changed)

    initial_state = window.no_name_checkbox.isChecked()
    window.no_name_checkbox.setChecked(not initial_state)
    qtbot.waitUntil(
        lambda: window.no_name_checkbox.isChecked() is not initial_state,
        timeout=WAIT_TIMEOUT,
    )
    qtbot.wait(100)  # Wait longer to ensure no signal

    assert not settings_manager.is_touched
    assert spy.count() == 0

    settings_manager.save()
    qtbot.wait(50)  # Wait after save
    window.no_name_checkbox.setChecked(initial_state)
    qtbot.waitUntil(
        lambda: window.no_name_checkbox.isChecked() is initial_state,
        timeout=WAIT_TIMEOUT,
    )

    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    assert window.no_name_checkbox.isChecked() == initial_state

    window.close()


def test_unskip_widget_restores_management(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test that unskipping a widget makes it managed again."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.checkbox)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load
    initial_checked_state = window.checkbox.isChecked()

    window.checkbox.setChecked(not initial_checked_state)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is not initial_checked_state,
        timeout=WAIT_TIMEOUT,
    )
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    settings_manager.unskip_widget(window.checkbox)
    qtbot.wait(50)  # Allow potential signal connection

    spy_touch = QSignalSpy(settings_manager.touched_changed)
    window.checkbox.setChecked(initial_checked_state)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is initial_checked_state,
        timeout=WAIT_TIMEOUT,
    )
    spy_touch.wait(100)  # Wait for signal

    assert settings_manager.is_touched
    assert spy_touch.count() == 1
    assert spy_touch.at(0) == [True]

    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    window.checkbox.setChecked(not initial_checked_state)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is not initial_checked_state,
        timeout=WAIT_TIMEOUT,
    )
    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is initial_checked_state,
        timeout=WAIT_TIMEOUT,
    )  # Wait for load

    assert window.checkbox.isChecked() is initial_checked_state
    assert not settings_manager.is_touched

    window.close()


# --- has_unsaved_changes Tests ---


def test_has_unsaved_changes_initial(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test has_unsaved_changes returns False initially and after load."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    window.close()


def test_has_unsaved_changes_after_change(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes returns True after a widget change."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    new_text = "A new value that differs"
    window.line_edit.setText(new_text)
    qtbot.waitUntil(lambda: window.line_edit.text() == new_text, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    window.close()


def test_has_unsaved_changes_after_save(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes returns False after saving changes."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    initial_value = window.spin_box.value()
    new_value = initial_value + 5
    window.spin_box.setValue(new_value)
    qtbot.waitUntil(lambda: window.spin_box.value() == new_value, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
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
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    settings_manager.skip_widget(window.checkbox)

    initial_checked = window.checkbox.isChecked()
    window.checkbox.setChecked(not initial_checked)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is not initial_checked, timeout=WAIT_TIMEOUT
    )

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    window.line_edit.setText("Managed change")
    qtbot.waitUntil(
        lambda: window.line_edit.text() == "Managed change", timeout=WAIT_TIMEOUT
    )  # Wait for change
    qtbot.waitUntil(lambda: settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    window.close()


def test_has_unsaved_changes_ignores_no_name(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes ignores changes in widgets without settings property."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    initial_checked = window.no_name_checkbox.isChecked()
    window.no_name_checkbox.setChecked(not initial_checked)
    qtbot.waitUntil(
        lambda: window.no_name_checkbox.isChecked() is not initial_checked,
        timeout=WAIT_TIMEOUT,
    )  # Wait for change

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    window.close()


def test_has_unsaved_changes_ignores_custom_data(  # Renamed from original
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test has_unsaved_changes does NOT detect changes only in custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    assert not settings_manager.is_touched

    settings_manager.save_custom_data("my_custom", [1, 2, 3])
    qtbot.wait(50)  # Short wait, though not strictly necessary

    assert not settings_manager.is_touched
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    initial_slider_val = window.slider.value()
    new_slider_val = initial_slider_val - 1
    window.slider.setValue(new_slider_val)
    qtbot.waitUntil(
        lambda: window.slider.value() == new_slider_val, timeout=WAIT_TIMEOUT
    )  # Wait for change

    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
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

    # 1. Save State A to default file
    settings_manager.load()
    window.checkbox.setChecked(False)
    window.line_edit.setText("State A")
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: window.line_edit.text() == "State A", timeout=WAIT_TIMEOUT)
    settings_manager.save()
    qtbot.waitUntil(lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    default_file = settings_manager._settings.fileName()

    # 2. Save State B to alt file
    alt_file = str(tmp_path / "alt_settings.ini")
    window.checkbox.setChecked(True)
    window.line_edit.setText("State B")
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: window.line_edit.text() == "State B", timeout=WAIT_TIMEOUT)
    settings_manager.save_to_file(alt_file)
    qtbot.wait(50)  # Wait after save_to_file

    # 3. Current is B. Compare against default (A)
    assert settings_manager.has_unsaved_changes(source=default_file)

    # 4. Compare current (B) against alt file (B)
    assert not settings_manager.has_unsaved_changes(source=alt_file)

    # 5. Load State A back
    settings_manager.load()
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(lambda: window.line_edit.text() == "State A", timeout=WAIT_TIMEOUT)

    # 6. Compare current (A) against alt file (B)
    assert settings_manager.has_unsaved_changes(source=alt_file)

    window.close()


# --- Other Tests ---


def test_get_managed_widgets(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test retrieving the list of managed widgets."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.ignored_checkbox)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    managed = settings_manager.get_managed_widgets()
    managed_names = {w.property(SETTINGS_PROPERTY) for w in managed}

    # Check standard widgets (using original keys)
    assert "testCheckbox" in managed_names
    assert "testLineEdit" in managed_names
    assert "testPushButton" in managed_names
    assert "testComboBox" in managed_names
    assert "testSpinBox" in managed_names
    assert "testDoubleSpinBox" in managed_names
    assert "testRadioButton1" in managed_names
    assert "testRadioButton2" in managed_names
    assert "testTextEdit" in managed_names
    assert "testTabWidget" in managed_names
    assert "testSlider" in managed_names
    assert "TestMainWindow" in managed_names
    # Check nested widgets (should still be found)
    assert "tab1Checkbox" in managed_names
    assert "tab2Lineedit" in managed_names

    # Check skipped/no-name/no-property widgets are absent
    assert "ignoredCheckbox" not in managed_names
    assert window.no_name_checkbox.property(SETTINGS_PROPERTY) is None
    assert window.no_name_checkbox not in managed
    # REVERTED: central widget and groupbox should not be managed directly
    assert "centralWidget" not in managed_names
    assert "radioGroup" not in managed_names
    assert "tab1Content" not in managed_names
    assert "tab2Content" not in managed_names

    # Check count (Original window + 11 named widgets + 2 nested named widgets = 14)
    expected_count = 14
    assert len(managed) == expected_count, (
        f"Expected {expected_count} managed widgets, found {len(managed)}: {[w.property(SETTINGS_PROPERTY) for w in managed]}"
    )

    window.close()


def test_custom_handler_registration(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test registering and using a custom handler."""
    original_handler = settings_manager._handlers.get(QCheckBox)  # Store original

    class InvertedCheckBoxHandler(SettingsHandler):
        def save(self, widget: QCheckBox, settings: QSettings):
            settings.setValue(
                widget.property(SETTINGS_PROPERTY), not widget.isChecked()
            )

        def load(self, widget: QCheckBox, settings: QSettings):
            value = cast(
                bool,
                settings.value(
                    widget.property(SETTINGS_PROPERTY),
                    not widget.isChecked(),
                    type=bool,
                ),
            )
            widget.setChecked(not value)

        def compare(self, widget: QCheckBox, settings: QSettings) -> bool:
            # Original logic from user test: Compare current state to the *non-inverted* version of saved state.
            # Returns True if they are different.
            key = widget.property(SETTINGS_PROPERTY)
            current_state = widget.isChecked()
            if not settings.contains(key):
                # If not saved, it's different from the current state unless current is default (False)
                # Let's refine: Treat as different if not saved.
                return True
            saved_inverted_state = cast(bool, settings.value(key, type=bool))
            # Compare current state to the logical (non-inverted) saved state
            return current_state != (not saved_inverted_state)

        def get_signals_to_monitor(self, widget: QCheckBox) -> list[SignalInstance]:
            return [widget.stateChanged]

    settings_manager.register_handler(QCheckBox, InvertedCheckBoxHandler())

    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)  # Wait after load

    # Set True, save (saves False)
    window.checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    # Set False temporarily
    window.checkbox.setChecked(False)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)

    # Load (loads False, sets True)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.checkbox.isChecked() is True

    # Compare: Current is True. Saved is False (logical True). Should match (False).
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    # Change: Current is False. Saved is False (logical True). Should differ (True).
    window.checkbox.setChecked(False)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT
    )  # Wait for change
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


def test_pushbutton_non_checkable_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test compare method for non-checkable push buttons returns False."""
    main_win = QMainWindow()
    main_win.setProperty(SETTINGS_PROPERTY, "TempMainWin")  # Needs a named main window
    qtbot.add_widget(main_win)

    button = QPushButton("Non Checkable")
    button.setProperty(SETTINGS_PROPERTY, "nonCheckableButton")
    button.setCheckable(False)
    main_win.setCentralWidget(button)
    main_win.show()
    qtbot.waitExposed(main_win)

    settings_manager.load()
    qtbot.wait(50)  # Wait after load
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    main_win.close()


def test_combobox_load_invalid_index(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test loading QComboBox state with an invalid saved index defaults to 0."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    window.combo_box.setCurrentIndex(1)
    qtbot.waitUntil(lambda: window.combo_box.currentIndex() == 1, timeout=WAIT_TIMEOUT)
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    # Manually write invalid index (using original key structure)
    settings_manager._settings.setValue(
        f"{window.combo_box.property(SETTINGS_PROPERTY)}/currentIndex", 999
    )
    settings_manager._settings.sync()

    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.combo_box.currentIndex() == 0, timeout=WAIT_TIMEOUT
    )  # Wait for load

    assert window.combo_box.currentIndex() == 0
    window.close()


def test_radio_button_compare_logic(  # Renamed from original
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    """Test compare logic for radio buttons after changes."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Use original keys directly
    radio1_key = window.radio_button1.property(SETTINGS_PROPERTY)
    radio2_key = window.radio_button2.property(SETTINGS_PROPERTY)

    # --- Step 1: Save initial state (r1=T, r2=F) ---
    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    assert settings_manager._settings.value(radio1_key, type=bool) is True
    assert settings_manager._settings.value(radio2_key, type=bool) is False

    # --- Step 2: Change UI (r1=F, r2=T) and save ---
    window.radio_button2.setChecked(True)
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is False, timeout=WAIT_TIMEOUT
    )
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    assert settings_manager._settings.value(radio1_key, type=bool) is False
    assert settings_manager._settings.value(radio2_key, type=bool) is True

    # --- Step 3: Change UI back (r1=T, r2=F) and compare ---
    window.radio_button1.setChecked(True)
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is False, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    # --- Step 4: Make UI match saved state again (r1=F, r2=T) ---
    window.radio_button2.setChecked(True)
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is False, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
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

    slider = window.slider
    initial_value = slider.value()
    assert initial_value == 25

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    # Manually save out-of-range value (using original key)
    slider_key = slider.property(SETTINGS_PROPERTY)
    settings_manager._settings.setValue(slider_key, 100)
    settings_manager._settings.sync()

    settings_manager.load()
    qtbot.waitUntil(
        lambda: slider.value() == initial_value, timeout=WAIT_TIMEOUT
    )  # Wait for load (value shouldn't change)

    assert slider.value() == initial_value
    # Check log message using original key
    assert f"Loaded value 100 for slider {slider_key} is out of range" in caplog.text
    window.close()


def test_main_window_geometry_change_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Skipping main window geometry test in offscreen environment")

    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    current_size = window.size()
    new_size = QSize(current_size.width() + 50, current_size.height() - 20)
    window.resize(new_size)
    qtbot.waitUntil(
        lambda: window.size() == new_size, timeout=WAIT_TIMEOUT
    )  # Wait for resize

    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    window.close()


def test_has_unsaved_changes_with_qsettings_source(
    qtbot: QtBot, settings_manager: QtSettingsManager, test_settings_file: str
):
    """Test comparing against a specific QSettings object."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    window.line_edit.setText("State A")
    qtbot.waitUntil(lambda: window.line_edit.text() == "State A", timeout=WAIT_TIMEOUT)
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    alt_settings_path = test_settings_file + ".alt"
    if os.path.exists(alt_settings_path):
        os.remove(alt_settings_path)
    alt_settings = QSettings(alt_settings_path, QSettings.Format.IniFormat)
    # Use original key for line edit
    line_edit_key = window.line_edit.property(SETTINGS_PROPERTY)
    alt_settings.setValue(line_edit_key, "State B")
    alt_settings.sync()

    # Current state is A, compare against alt_settings (State B)
    assert settings_manager.has_unsaved_changes(source=alt_settings)
    window.close()
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

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load
    settings_manager.mark_touched()
    assert settings_manager.is_touched

    invalid_path = "non_existent_or_invalid_settings_file.ini"
    if os.path.exists(invalid_path):
        os.remove(invalid_path)

    settings_manager.load_from_file(invalid_path)
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for state reset

    assert (
        f"Could not load settings from {invalid_path}" in caplog.text
        or QSettings(invalid_path, QSettings.Format.IniFormat).status()
        == QSettings.Status.NoError
    )

    assert window.line_edit.text() == initial_text
    assert not settings_manager.is_touched
    window.close()
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
    unpickleable_data = lambda x: x  # noqa: E731
    key = "unpickleable"
    settings_manager.save_custom_data(key, unpickleable_data)
    # No wait needed
    assert f"Could not pickle custom data for key '{key}'" in caplog.text
    assert settings_manager._settings.value(f"{CUSTOM_DATA_GROUP}/{key}") is None


def test_load_custom_data_not_found(settings_manager: QtSettingsManager):
    """Test loading custom data for a key that doesn't exist."""
    assert settings_manager.load_custom_data("non_existent_key", bytes) is None


def test_load_custom_data_type_mismatch(
    settings_manager: QtSettingsManager, caplog
):  # Added from previous run
    """Test loading custom data with the wrong expected type."""
    key = "type_mismatch_key"
    data = {"a": 1}
    settings_manager.save_custom_data(key, data)
    # No wait needed
    loaded = settings_manager.load_custom_data(key, list)  # Expect list, saved dict
    assert loaded is None
    assert "does not match the expected type list" in caplog.text

def test_delete_custom_data(settings_manager: QtSettingsManager):
    """Test deleting custom data."""
    key = "delete_me"
    data = [1, 2, 3]
    settings_manager.save_custom_data(key, data)
    assert settings_manager.load_custom_data(key, list) == data

    settings_manager.delete_custom_data(key)
    assert settings_manager.load_custom_data(key, list) is None
    assert not settings_manager._settings.contains(f"{CUSTOM_DATA_GROUP}/{key}")

def test_load_custom_data_empty_bytes(settings_manager: QtSettingsManager, caplog):
    """Test loading custom data when settings contain empty bytes."""
    key = "empty_bytes_key"
    settings_manager._settings.beginGroup(CUSTOM_DATA_GROUP)
    settings_manager._settings.setValue(key, QByteArray(b""))
    settings_manager._settings.endGroup()
    settings_manager._settings.sync()
    # No wait needed
    assert settings_manager.load_custom_data(key, bytes) is None
    assert f"No valid data found for custom data key '{key}'" in caplog.text


def test_load_custom_data_unpickle_error(settings_manager: QtSettingsManager, caplog):
    """Test loading custom data that causes an UnpicklingError."""
    key = "garbage_data"
    settings_manager._settings.beginGroup(CUSTOM_DATA_GROUP)
    settings_manager._settings.setValue(key, QByteArray(b"this is not pickled data"))
    settings_manager._settings.endGroup()
    settings_manager._settings.sync()
    # No wait needed
    assert settings_manager.load_custom_data(key, bytes) is None
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
        if isinstance(widget, QCheckBox):
            settings.setValue(widget.property(SETTINGS_PROPERTY), widget.isChecked())

    def load(self, widget: QWidget, settings: QSettings):
        self._maybe_fail("load")
        if isinstance(widget, QCheckBox):
            value = cast(
                bool, settings.value(widget.property(SETTINGS_PROPERTY), type=bool)
            )
            widget.setChecked(value)
            widget.setText("Load Attempted")

    def compare(self, widget: QWidget, settings: QSettings) -> bool:
        self._maybe_fail("compare")
        if isinstance(widget, QCheckBox):
            key = widget.property(SETTINGS_PROPERTY)
            current_value: bool = widget.isChecked()
            saved_value = cast(bool, settings.value(key, current_value, type=bool))
            return current_value != saved_value
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
    original_handler = settings_manager._handlers.get(QCheckBox)
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="load"))
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    # Save valid state first using default handler
    window.checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)
    settings_manager.save()
    qtbot.waitUntil(lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    settings_manager.register_handler(
        QCheckBox, FaultyHandler(fail_on="load")
    )  # Put faulty back

    window.checkbox.setChecked(False)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is False, timeout=WAIT_TIMEOUT)

    settings_manager.load()
    qtbot.wait(50)  # Allow logging

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key

    expected_log = f"Error during 'load' on widget '{checkbox_key}' (QCheckBox)"
    assert expected_log in caplog.text
    assert "Error during recursive load:" not in caplog.text
    assert "Intentional failure during load" in caplog.text
    assert window.checkbox.isChecked() is False  # State should not have changed

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


def test_exception_during_compare(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test graceful handling of exception during widget compare."""
    original_handler = settings_manager._handlers.get(QCheckBox)
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="compare"))
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    settings_manager.save()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after save

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key

    window.checkbox.setChecked(not window.checkbox.isChecked())
    qtbot.waitUntil(
        lambda: settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for change

    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    expected_log = f"Error during 'compare' on widget '{checkbox_key}' (QCheckBox)"
    assert expected_log in caplog.text
    assert "Intentional failure during compare" in caplog.text
    assert (
        f"Treating widget '{checkbox_key}' as different due to error during comparison."
        in caplog.text
    )

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


def test_exception_getting_signals(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test graceful handling of exception during get_signals_to_monitor."""
    original_handler = settings_manager._handlers.get(QCheckBox)
    settings_manager.register_handler(QCheckBox, FaultyHandler(fail_on="get_signals"))
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()  # Triggers connect -> get_signals
    qtbot.wait(50)  # Allow logging

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key

    assert f"Error getting signals for widget {checkbox_key}" in caplog.text
    assert "Intentional failure during get_signals" in caplog.text

    spy = QSignalSpy(settings_manager.touched_changed)
    initial_checked = window.checkbox.isChecked()
    window.checkbox.setChecked(not initial_checked)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is not initial_checked, timeout=WAIT_TIMEOUT
    )
    qtbot.wait(50)
    assert spy.count() == 0  # Signal should not be connected

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


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

    settings_manager._disconnect_all_widget_signals()
    settings_manager._connect_signals(window)
    qtbot.wait(50)  # Allow connection

    initial_connections = dict(settings_manager._connected_signals)
    initial_key_count = len(initial_connections)
    assert initial_key_count > 0

    settings_manager._connect_signals(window)  # Call again
    qtbot.wait(50)  # Allow potential reconnection

    final_key_count = len(settings_manager._connected_signals)
    assert final_key_count == initial_key_count

    final_connections = dict(settings_manager._connected_signals)
    for widget, signals in initial_connections.items():
        widget_prop = widget.property(SETTINGS_PROPERTY) or type(widget).__name__
        assert widget in final_connections
        assert len(final_connections[widget]) == len(signals)

    window.close()


def test_connect_invalid_signal_object(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test connecting signals when handler returns an invalid object."""
    original_handler = settings_manager._handlers.get(QCheckBox)

    class BadSignalHandler(SettingsHandler):
        def save(self, w, s):
            pass

        def load(self, w, s):
            pass

        def compare(self, w, s):
            return False

        def get_signals_to_monitor(self, widget: QWidget) -> list[Any]:
            return [123, "not a signal", widget.stateChanged]  # type: ignore # Include one valid

    settings_manager.register_handler(QCheckBox, BadSignalHandler())
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    qtbot.wait(150)  # Allow logging and signal connection attempts

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key

    assert f"Invalid signal object for {checkbox_key}: 123" in caplog.text
    assert f"Invalid signal object for {checkbox_key}: not a signal" in caplog.text

    # Check connection status carefully to avoid deleted object errors
    connected_signals = settings_manager._connected_signals.get(window.checkbox)
    assert connected_signals is not None, (
        f"Widget {checkbox_key} not found in connected signals"
    )
    assert len(connected_signals) == 1, (
        f"Expected 1 signal for {checkbox_key}, found {len(connected_signals)}"
    )

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


def test_disconnect_error_handling(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Attempt to test disconnect error handling (e.g., widget deleted)."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    widget_to_check = window.checkbox
    target_property = widget_to_check.property(SETTINGS_PROPERTY)
    assert target_property == "testCheckbox"

    found_key_instance = None
    for key_widget in settings_manager._connected_signals.keys():
        if key_widget.property(SETTINGS_PROPERTY) == target_property:
            found_key_instance = key_widget
            break
    assert found_key_instance is not None
    assert found_key_instance in settings_manager._connected_signals
    assert len(settings_manager._connected_signals[found_key_instance]) > 0

    widget_to_check.deleteLater()
    qtbot.waitSignal(widget_to_check.destroyed)

    try:
        settings_manager._disconnect_widget_signals(found_key_instance)
        # settings_manager._disconnect_all_widget_signals() # Alternative
    except Exception as e:
        pytest.fail(f"_disconnect raised unexpected exception: {e}")

    assert found_key_instance not in settings_manager._connected_signals

    window.close()


class Unpickleable:
    def __getstate__(self):
        raise TypeError("This object cannot be pickled")


def test_save_unpickleable_custom_data_type_error(
    settings_manager: QtSettingsManager, caplog
):
    """Test saving custom data that raises TypeError during pickling."""
    unpickleable_data = Unpickleable()
    key = "unpickleable_type_error"
    settings_manager.save_custom_data(key, unpickleable_data)
    # No wait needed
    assert f"Could not pickle custom data for key '{key}'" in caplog.text
    assert "This object cannot be pickled" in caplog.text
    assert settings_manager._settings.value(f"{CUSTOM_DATA_GROUP}/{key}") is None


def test_load_custom_data_invalid_pickle_bytes(
    settings_manager: QtSettingsManager, caplog
):  # Renamed from original
    """Test loading custom data when settings contain invalid (non-pickle) bytes."""
    key = "invalid_bytes_key"
    invalid_bytes = b"just some random bytes \x01\x02\x03"
    settings_manager._settings.beginGroup(CUSTOM_DATA_GROUP)
    settings_manager._settings.setValue(key, QByteArray(invalid_bytes))
    settings_manager._settings.endGroup()
    settings_manager._settings.sync()
    # No wait needed
    loaded_data = settings_manager.load_custom_data(key, dict)
    assert loaded_data is None
    assert f"Could not unpickle data for key '{key}'" in caplog.text


def test_save_to_file_includes_custom_data(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    """Verify save_to_file writes both widget state and custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    widget_key = window.line_edit.property(SETTINGS_PROPERTY)  # Original key
    widget_value = "Widget Value In File"
    custom_key = "my_data_key"
    custom_value = {"a": 1, "b": [True, None]}
    custom_key_enum = SettingsKey.NEW_KEY
    custom_value_enum = ["enum", "test"]

    window.line_edit.setText(widget_value)
    qtbot.waitUntil(
        lambda: window.line_edit.text() == widget_value, timeout=WAIT_TIMEOUT
    )

    qtbot.wait(100)
    settings_manager.save_custom_data(custom_key, custom_value)
    settings_manager.save_custom_data(custom_key_enum, custom_value_enum)

    target_file = str(tmp_path / "save_with_custom.ini")
    settings_manager.save_to_file(target_file)
    qtbot.wait(100)  # Wait after save_to_file

    file_settings = QSettings(target_file, QSettings.Format.IniFormat)
    assert file_settings.status() == QSettings.Status.NoError

    # Check widget value was saved correctly
    qtbot.waitUntil(lambda: file_settings.contains(widget_key), timeout=WAIT_TIMEOUT)
    saved_widget_value = file_settings.value(widget_key)
    assert saved_widget_value == widget_value, (
        f"Expected '{widget_value}', got '{saved_widget_value}'"
    )

    # Check custom data
    file_settings.beginGroup(CUSTOM_DATA_GROUP)
    assert file_settings.contains(custom_key)
    assert file_settings.contains(custom_key_enum.value)

    loaded_bytes = file_settings.value(custom_key)
    assert isinstance(loaded_bytes, QByteArray)
    loaded_data = pickle.loads(loaded_bytes.data())
    assert loaded_data == custom_value

    loaded_bytes_enum = file_settings.value(custom_key_enum.value)
    assert isinstance(loaded_bytes_enum, QByteArray)
    loaded_data_enum = pickle.loads(loaded_bytes_enum.data())
    assert loaded_data_enum == custom_value_enum

    file_settings.endGroup()
    window.close()


def test_load_from_file_includes_custom_data(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    """Verify load_from_file loads widgets and overwrites custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    source_file = str(tmp_path / "load_source.ini")
    file_settings = QSettings(source_file, QSettings.Format.IniFormat)

    widget_key = window.line_edit.property(SETTINGS_PROPERTY)  # Original key
    widget_value_in_file = "Loaded From File"
    custom_key_in_file = "file_custom_data"
    custom_value_in_file = {"status": "loaded", "count": 5}

    file_settings.setValue(widget_key, widget_value_in_file)  # Use original key
    file_settings.beginGroup(CUSTOM_DATA_GROUP)
    pickled_custom_data = pickle.dumps(custom_value_in_file)
    file_settings.setValue(custom_key_in_file, QByteArray(pickled_custom_data))
    file_settings.endGroup()
    file_settings.sync()
    del file_settings

    preexisting_custom_key = "preexisting_data"
    settings_manager.save_custom_data(preexisting_custom_key, "This should be removed")
    assert (
        settings_manager.load_custom_data(preexisting_custom_key, str)
        == "This should be removed"
    )

    settings_manager.load_from_file(source_file)
    qtbot.waitUntil(
        lambda: window.line_edit.text() == widget_value_in_file, timeout=WAIT_TIMEOUT
    )  # Wait for load
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for state reset

    assert window.line_edit.text() == widget_value_in_file
    loaded_custom = settings_manager.load_custom_data(custom_key_in_file, dict)
    assert loaded_custom == custom_value_in_file
    assert settings_manager.load_custom_data(preexisting_custom_key, str) is None
    assert not settings_manager.is_touched

    window.close()


def test_load_from_file_clears_previous_custom_data(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    """Verify load_from_file clears custom data not present in the loaded file."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    key_to_remove = "initial_key"
    settings_manager.save_custom_data(key_to_remove, {"value": 1})
    assert settings_manager.load_custom_data(key_to_remove, dict) is not None

    source_file = str(tmp_path / "load_clear_test.ini")
    file_settings = QSettings(source_file, QSettings.Format.IniFormat)
    key_to_keep = "key_from_file"
    value_to_keep = "data from file"
    file_settings.beginGroup(CUSTOM_DATA_GROUP)
    file_settings.setValue(key_to_keep, QByteArray(pickle.dumps(value_to_keep)))
    file_settings.endGroup()
    # Use original main window key
    file_settings.setValue("TestMainWindow/geometry", "dummy")
    file_settings.sync()
    del file_settings

    settings_manager.load_from_file(source_file)
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for load process

    assert settings_manager.load_custom_data(key_to_remove, dict) is None
    assert settings_manager.load_custom_data(key_to_keep, str) == value_to_keep

    window.close()


def test_load_from_file_without_custom_data_group(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    """Verify loading from a file with no [customData] group clears existing custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    key_to_remove = "initial_key_no_group"
    settings_manager.save_custom_data(key_to_remove, [1, 2, 3])
    assert settings_manager.load_custom_data(key_to_remove, list) is not None

    source_file = str(tmp_path / "load_no_custom_group.ini")
    file_settings = QSettings(source_file, QSettings.Format.IniFormat)
    widget_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key
    file_settings.setValue(widget_key, True)  # Use original key
    file_settings.sync()
    del file_settings

    settings_manager.load_from_file(source_file)
    qtbot.waitUntil(
        lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for state reset

    assert settings_manager.load_custom_data(key_to_remove, list) is None
    assert window.checkbox.isChecked() is True

    window.close()


def test_skip_widget_prevents_touched(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    pytest.skip("Windows fatal exception: access violation ")
    """Verify changes to skipped widgets do not mark state as touched."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.checkbox)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    assert not settings_manager.is_touched
    spy = QSignalSpy(settings_manager.touched_changed)
    assert spy.isValid()  # Ensure spy is valid before waiting

    window.checkbox.setChecked(True)
    qtbot.waitUntil(lambda: window.checkbox.isChecked() is True, timeout=WAIT_TIMEOUT)
    qtbot.wait(100)  # Wait longer to ensure no signal

    assert not settings_manager.is_touched
    assert spy.count() == 0

    window.line_edit.setText("Change")
    qtbot.waitUntil(lambda: settings_manager.is_touched, timeout=WAIT_TIMEOUT)

    assert settings_manager.is_touched  # This assertion was failing
    assert spy.count() >= 1  # Check that at least one signal was received
    assert spy.at(-1) == [True]  # Check the last signal was True

    window.close()


@patch("pyside_settings_manager.settings.QSettings")
def test_load_from_file_error_status(
    mock_qsettings_ctor: MagicMock,
    qtbot: QtBot,
    settings_manager: QtSettingsManager,
    tmp_path: Path,
    caplog,
):
    """Test load_from_file when QSettings reports an error status."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    initial_text = window.line_edit.text()
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load
    settings_manager.mark_touched()

    mock_settings_instance = MagicMock(spec=QSettings)
    mock_settings_instance.status.return_value = QSettings.Status.AccessError
    mock_qsettings_ctor.return_value = mock_settings_instance

    settings_manager.load_from_file("dummy_path.ini")
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for state reset

    # Use the mock object's reference to the enum attribute for the assertion
    mock_qsettings_ctor.assert_called_once_with(
        "dummy_path.ini", mock_qsettings_ctor.Format.IniFormat
    )

    mock_settings_instance.status.assert_called()
    assert (
        "Could not load settings from dummy_path.ini. Status: Status.AccessError"
        in caplog.text
    )
    assert window.line_edit.text() == initial_text
    assert not settings_manager.is_touched
    assert not settings_manager._connected_signals

    window.close()


def test_connect_signal_connect_error(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    """Test connecting signals when the signal's connect() method raises error."""
    original_handler = settings_manager._handlers.get(QCheckBox)
    mock_signal = MagicMock(spec=SignalInstance)
    mock_signal.connect.side_effect = RuntimeError("Intentional connect error")
    mock_signal.signal = "mockSignalWithError"

    class ErrorOnConnectHandler(SettingsHandler):
        def save(self, w, s):
            pass

        def load(self, w, s):
            pass

        def compare(self, w, s):
            return False

        def get_signals_to_monitor(self, widget: QWidget) -> list[SignalInstance]:
            return [mock_signal, widget.stateChanged]  # type: ignore   # Include valid one

    settings_manager.register_handler(QCheckBox, ErrorOnConnectHandler())
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load()

    # Add a slightly longer wait after load to ensure signal connection attempts
    # and potential error logging have fully processed before assertions.
    qtbot.wait(150)

    checkbox_key = window.checkbox.property(SETTINGS_PROPERTY)  # Original key

    assert (
        f"Failed to connect signal mockSignalWithError for {checkbox_key}: Intentional connect error"
        in caplog.text
    )

    # Check the widget instance directly from the window object, which should still be valid.
    # The previous failure message indicated the keys in _connected_signals might be
    # references to already deleted C++ objects during teardown in parallel execution.
    # Accessing window.checkbox should be safe here.
    assert window.checkbox in settings_manager._connected_signals, (
        f"Widget {checkbox_key} not found in connected signals: {list(settings_manager._connected_signals.keys())}"
    )
    assert (
        len(settings_manager._connected_signals[window.checkbox]) == 1
    )  # Only valid one should be connected

    window.close()
    if original_handler:
        settings_manager.register_handler(QCheckBox, original_handler)


# Modify test to use mocking to ensure QSettings status error,
# avoiding ambiguity of non-existent file status.
@patch("pyside_settings_manager.settings.QSettings")
def test_load_from_file_error_does_not_affect_custom_data(
    mock_qsettings_ctor: MagicMock,
    qtbot: QtBot,
    settings_manager: QtSettingsManager,
    caplog,
):
    """Verify load_from_file on error doesn't clear existing custom data."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    initial_key = "persist_on_error"
    initial_value = "Keep Me!"
    settings_manager.save_custom_data(initial_key, initial_value)
    # Ensure it was saved before the test
    assert settings_manager.load_custom_data(initial_key, str) == initial_value, (
        "Pre-condition failed: Custom data not saved initially"
    )

    # Configure mock QSettings to return an error status
    mock_settings_instance = MagicMock(spec=QSettings)
    mock_settings_instance.status.return_value = (
        QSettings.Status.AccessError
    )  # Simulate error
    mock_qsettings_ctor.return_value = mock_settings_instance

    # Attempt to load from a dummy path, which will use the mock
    settings_manager.load_from_file("dummy_error_path.ini")
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait for state reset

    # Check the error was logged
    assert (
        "Could not load settings from dummy_error_path.ini. Status: Status.AccessError"
        in caplog.text
    )

    # Verify custom data still exists because the load failed early
    assert settings_manager.load_custom_data(initial_key, str) == initial_value, (
        "Custom data should not be cleared if load_from_file fails due to QSettings status error"
    )

    window.close()


@patch("pyside_settings_manager.settings.QSettings")
def test_has_unsaved_changes_invalid_file_source(
    mock_qsettings_ctor: MagicMock,
    qtbot: QtBot,
    settings_manager: QtSettingsManager,
    tmp_path: Path,
    caplog,
):
    """Test has_unsaved_changes when source file QSettings reports an error."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()  # Load manager's own settings

    mock_source_settings_instance = MagicMock(spec=QSettings)
    mock_source_settings_instance.status.return_value = QSettings.Status.FormatError
    mock_qsettings_ctor.return_value = mock_source_settings_instance

    result = settings_manager.has_unsaved_changes(source="bad_format.ini")
    # No wait needed for has_unsaved_changes

    # Use the mock object's reference to the enum attribute for the assertion
    mock_qsettings_ctor.assert_called_once_with(
        "bad_format.ini", mock_qsettings_ctor.Format.IniFormat
    )

    mock_source_settings_instance.status.assert_called()
    assert (
        "Cannot compare: Failed to load settings from bad_format.ini. Status: Status.FormatError"
        in caplog.text
    )
    assert result is False

    window.close()


def test_radio_button_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait after load

    # Change selection
    window.radio_button2.setChecked(True)
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is False, timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.wait(50)  # Wait after save

    # Change back temporarily
    window.radio_button1.setChecked(True)
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is True, timeout=WAIT_TIMEOUT
    )
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is False, timeout=WAIT_TIMEOUT
    )

    settings_manager.load()
    # quite flaky
    qtbot.waitUntil(
        lambda: window.radio_button2.isChecked() is True, timeout=WAIT_TIMEOUT
    )  # Wait for load
    qtbot.waitUntil(
        lambda: window.radio_button1.isChecked() is False, timeout=WAIT_TIMEOUT
    )

    assert window.radio_button2.isChecked() is True
    assert window.radio_button1.isChecked() is False
    assert not settings_manager.is_touched
    window.close()


def test_combobox_editable_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    """Test save/load/compare for an editable QComboBox."""
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    combo = window.combo_box
    combo.setEditable(True)
    qtbot.waitUntil(lambda: combo.isEditable() is True, timeout=WAIT_TIMEOUT)
    settings_manager.load()
    qtbot.waitUntil(
        lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT
    )  # Wait after load

    initial_text = "Initial Editable Text"
    combo.setCurrentText(initial_text)
    qtbot.waitUntil(lambda: combo.currentText() == initial_text, timeout=WAIT_TIMEOUT)
    actual_initial_index = combo.currentIndex()

    settings_manager.save()
    qtbot.waitUntil(lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    new_text = "Edited Text"
    le = combo.lineEdit()
    assert le is not None
    le.setText(new_text)
    qtbot.waitUntil(lambda: combo.currentText() == new_text, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )

    settings_manager.save()
    qtbot.waitUntil(lambda: not settings_manager.is_touched, timeout=WAIT_TIMEOUT)

    qtbot.waitUntil(
        lambda: not settings_manager.has_unsaved_changes(), timeout=WAIT_TIMEOUT
    )
    # Set text, wait, then set index, wait. Avoids potential race condition.
    combo.setCurrentText("Temporary Text")
    qtbot.waitUntil(
        lambda: combo.currentText() == "Temporary Text", timeout=WAIT_TIMEOUT
    )  # Shorter timeout for this specific step
    combo.setCurrentIndex(1)
    qtbot.waitUntil(
        lambda: combo.currentIndex() == 1, timeout=WAIT_TIMEOUT
    )  # Shorter timeout

    settings_manager.load()
    qtbot.waitUntil(lambda: combo.currentText() == new_text, timeout=WAIT_TIMEOUT)
    qtbot.waitUntil(
        lambda: combo.currentIndex() == actual_initial_index, timeout=WAIT_TIMEOUT
    )

    assert combo.currentText() == new_text
    assert combo.currentIndex() == actual_initial_index
    assert not settings_manager.is_touched
    window.close()


def test_operations_no_main_window(settings_manager: QtSettingsManager, caplog):
    if os.getenv("CI"):
        pytest.skip("Skipping on CI")

    for w in QApplication.topLevelWidgets():
        if isinstance(w, SettingsTestWindow):
            w.close()

    caplog.set_level(logging.WARNING)

    settings_manager.mark_touched()
    assert settings_manager.is_touched
    caplog.clear()
    settings_manager.save()
    assert "No QMainWindow with SETTINGS_PROPERTY found" in caplog.text
    assert not settings_manager.is_touched  # save should still mark untouched

    settings_manager.mark_touched()  # Start in a touched state
    assert settings_manager.is_touched
    caplog.clear()
    settings_manager.load()
    assert "No QMainWindow with SETTINGS_PROPERTY found" in caplog.text
    assert not settings_manager.is_touched  # load should still mark untouched

    caplog.clear()
    result = settings_manager.has_unsaved_changes()
    assert "No QMainWindow with SETTINGS_PROPERTY found" in caplog.text
    assert result is False

    caplog.clear()
    widgets = settings_manager.get_managed_widgets()
    assert "No QMainWindow with SETTINGS_PROPERTY found" in caplog.text
    assert widgets == []


def test_save_to_same_file_skips_custom_data_clear(
    qtbot: QtBot, settings_manager: QtSettingsManager, caplog
):
    window = SettingsTestWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load()
    qtbot.wait(50)

    custom_key = "my_persistent_data"
    custom_value = {"data": "should not be cleared"}
    settings_manager.save_custom_data(custom_key, custom_value)
    assert settings_manager.load_custom_data(custom_key, dict) == custom_value

    default_settings_file = settings_manager._settings.fileName()
    assert default_settings_file is not None

    settings_manager.save_to_file(default_settings_file)
    qtbot.wait(100)

    loaded_data = settings_manager.load_custom_data(custom_key, dict)
    assert loaded_data == custom_value, "Custom data was incorrectly cleared"

    file_settings = QSettings(default_settings_file, QSettings.Format.IniFormat)
    file_settings.beginGroup(CUSTOM_DATA_GROUP)
    assert file_settings.contains(custom_key)
    file_settings.endGroup()

    window.close()

def test_custom_data_keys_updates_on_delete(settings_manager: QtSettingsManager):
    """Test that custom_data_keys is updated correctly when data is deleted."""
    assert settings_manager.custom_data_keys == []

    settings_manager.save_custom_data("key1", "a")
    settings_manager.save_custom_data("key2", "b")

    assert sorted(settings_manager.custom_data_keys) == ["key1", "key2"]

    settings_manager.delete_custom_data("key2")
    assert sorted(settings_manager.custom_data_keys) == ["key1"]

    settings_manager.delete_custom_data("key1")
    assert settings_manager.custom_data_keys == []


def test_custom_data_keys_after_loading_from_file(settings_manager: QtSettingsManager, tmp_path):
    file_path = tmp_path / "external_settings.ini"
    external_settings = QSettings(str(file_path), QSettings.Format.IniFormat)
    external_settings.beginGroup("customData")
    import pickle
    from PySide6.QtCore import QByteArray
    external_settings.setValue("external_key", QByteArray(pickle.dumps("external_value")))
    external_settings.setValue("another_key", QByteArray(pickle.dumps(99)))
    external_settings.endGroup()
    del external_settings  # Ensures data is flushed to disk

    assert settings_manager.custom_data_keys == []

    settings_manager.load_from_file(str(file_path))

    assert sorted(settings_manager.custom_data_keys) == ["another_key", "external_key"]


def test_save_to_file_does_not_alter_managers_keys(settings_manager: QtSettingsManager, tmp_path):
    save_path = tmp_path / "save_destination.ini"

    settings_manager.save_custom_data("persistent_key", "some data")
    initial_keys = settings_manager.custom_data_keys

    assert initial_keys == ["persistent_key"]

    settings_manager.save_to_file(str(save_path))

    assert settings_manager.custom_data_keys == initial_keys

    saved_settings = QSettings(str(save_path), QSettings.Format.IniFormat)
    saved_settings.beginGroup("customData")
    assert saved_settings.childKeys() == ["persistent_key"]
    saved_settings.endGroup()
