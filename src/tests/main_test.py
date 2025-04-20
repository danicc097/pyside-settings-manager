import os
from typing import Generator
from PySide6.QtTest import QSignalSpy
import pytest
import sys
from pathlib import Path


from PySide6.QtCore import Qt, QSettings, QSize, Signal, SignalInstance
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

from pytestqt.qtbot import QtBot  # type: ignore


from pyside_settings_manager.settings import (
    create_settings_manager,
    QtSettingsManager,
    SignalMonitor,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def test_settings_file(tmp_path: Path) -> str:
    fpath = tmp_path / "test_app_settings_poc.ini"
    return str(fpath)


@pytest.fixture
def settings_manager(
    test_settings_file: str,
) -> Generator[QtSettingsManager, None, None]:
    if os.path.exists(test_settings_file):
        os.remove(test_settings_file)
    settings = QSettings(test_settings_file, QSettings.Format.IniFormat)
    manager = create_settings_manager(settings)
    assert isinstance(manager, QtSettingsManager)
    yield manager
    settings.clear()
    del settings
    if os.path.exists(test_settings_file):
        try:
            os.remove(test_settings_file)
        except OSError:
            pass


class TestSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("TestMainWindow")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.checkbox = QCheckBox("Test Checkbox")
        self.checkbox.setObjectName("testCheckbox")
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("testLineEdit")
        self.push_button = QPushButton("Test Button")
        self.push_button.setObjectName("testPushButton")
        self.push_button.setCheckable(True)
        self.combo_box = QComboBox()
        self.combo_box.setObjectName("testComboBox")
        self.combo_box.addItems(["Option 1", "Option 2", "Option 3"])
        self.spin_box = QSpinBox()
        self.spin_box.setObjectName("testSpinBox")
        self.spin_box.setRange(0, 100)
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("testTextEdit")
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("testTabWidget")
        self.tab_widget.addTab(QWidget(), "Tab 1")
        self.tab_widget.addTab(QWidget(), "Tab 2")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("testSlider")
        self.slider.setRange(0, 100)
        self.radio_button = QRadioButton("Test Radio Button")
        self.radio_button.setObjectName("testRadioButton")
        self.double_spin_box = QDoubleSpinBox()
        self.double_spin_box.setObjectName("testDoubleSpinBox")
        self.ignored_checkbox = QCheckBox("Ignored Checkbox")

        layout.addWidget(self.checkbox)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.push_button)
        layout.addWidget(self.combo_box)
        layout.addWidget(self.spin_box)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.slider)
        layout.addWidget(self.radio_button)
        layout.addWidget(self.double_spin_box)
        layout.addWidget(self.ignored_checkbox)


def test_save_load_main_window(qtbot: QtBot, settings_manager: QtSettingsManager):
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Skipping main window geometry test in offscreen environment")
    main_window = QMainWindow()
    main_window.setObjectName("mainWindowGeoTest")
    qtbot.add_widget(main_window)
    main_window.resize(800, 600)
    main_window.show()
    qtbot.waitExposed(main_window)
    settings_manager.load_state()
    settings_manager.save_state()
    main_window.resize(640, 480)
    qtbot.wait(50)
    settings_manager.save_state()
    main_window.resize(300, 200)
    qtbot.wait(50)
    settings_manager.load_state()
    qtbot.wait(50)
    assert main_window.size() == QSize(640, 480)
    assert not settings_manager.is_dirty
    main_window.close()


def test_checkbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    window.checkbox.setChecked(True)
    settings_manager.save_state()
    window.checkbox.setChecked(False)
    settings_manager.load_state()
    assert window.checkbox.isChecked() is True
    assert not settings_manager.is_dirty
    window.close()


def test_lineedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_text = "Test content"
    window.line_edit.setText(test_text)
    settings_manager.save_state()
    window.line_edit.clear()
    settings_manager.load_state()
    assert window.line_edit.text() == test_text
    assert not settings_manager.is_dirty
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
    assert not settings_manager.is_dirty
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
    assert not settings_manager.is_dirty
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
    assert not settings_manager.is_dirty
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
    window.double_spin_box.setValue(0)
    settings_manager.load_state()
    assert abs(window.double_spin_box.value() - test_value) < 0.001
    assert not settings_manager.is_dirty
    window.close()


def test_radio_button_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    window.radio_button.setChecked(True)
    settings_manager.save_state()
    other_radio = QRadioButton("Other", window.centralWidget())
    if layout := window.centralWidget().layout():
        layout.addWidget(other_radio)
    other_radio.setChecked(True)
    settings_manager.load_state()
    assert window.radio_button.isChecked() is True
    assert not settings_manager.is_dirty
    window.close()


def test_textedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_text = "Multi\nline\ntext"
    window.text_edit.setPlainText(test_text)
    settings_manager.save_state()
    window.text_edit.clear()
    settings_manager.load_state()
    assert window.text_edit.toPlainText() == test_text
    assert not settings_manager.is_dirty
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
    assert not settings_manager.is_dirty
    window.close()


def test_slider_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()
    test_value = 75
    window.slider.setValue(test_value)
    settings_manager.save_state()
    window.slider.setValue(0)
    settings_manager.load_state()
    assert window.slider.value() == test_value
    assert not settings_manager.is_dirty
    window.close()


def test_initial_state_is_clean(settings_manager: QtSettingsManager):
    assert not settings_manager.is_dirty


def test_load_state_makes_clean(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.mark_dirty()
    assert settings_manager.is_dirty

    spy = QSignalSpy(settings_manager.dirty_changed)
    settings_manager.load_state()
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert not settings_manager.is_dirty
    assert spy.count() == 1

    assert spy.at(0) == [False]
    window.close()


def test_save_state_makes_clean(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()

    spy = QSignalSpy(settings_manager.dirty_changed)
    window.checkbox.setChecked(not window.checkbox.isChecked())
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)
    assert settings_manager.is_dirty
    assert spy.count() >= 1

    spy_save = QSignalSpy(settings_manager.dirty_changed)
    settings_manager.save_state()
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert not settings_manager.is_dirty
    assert spy_save.count() == 1
    assert spy_save.at(0) == [False]
    window.close()


def test_widget_change_marks_dirty(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()
    assert not settings_manager.is_dirty

    spy = QSignalSpy(settings_manager.dirty_changed)
    assert spy.isValid()

    window.checkbox.setChecked(True)
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [True]

    signals_received = spy.count()

    window.line_edit.setText("New Text")
    qtbot.wait(100)

    assert spy.count() == signals_received

    window.slider.setValue(window.slider.value() + 10)
    qtbot.wait(100)
    assert spy.count() == signals_received

    assert settings_manager.is_dirty
    window.close()


def test_save_custom_data_marks_dirty(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    settings_manager.load_state()
    assert not settings_manager.is_dirty

    spy = QSignalSpy(settings_manager.dirty_changed)
    settings_manager.save_custom_data("custom_key", {"value": 1})
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [True]

    signals_received = spy.count()

    settings_manager.save_custom_data("custom_key", {"value": 2})
    qtbot.wait(50)
    assert spy.count() == signals_received


def test_skip_widget_prevents_dirty(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.skip_widget(window.checkbox)
    settings_manager.load_state()

    assert not settings_manager.is_dirty
    spy = QSignalSpy(settings_manager.dirty_changed)

    window.checkbox.setChecked(True)
    qtbot.wait(100)

    assert not settings_manager.is_dirty
    assert spy.count() == 0

    window.line_edit.setText("Change")
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)
    assert settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [True]

    window.close()


def test_widget_without_objectname_not_monitored(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()

    assert not settings_manager.is_dirty
    spy = QSignalSpy(settings_manager.dirty_changed)

    window.ignored_checkbox.setChecked(True)
    qtbot.wait(100)

    assert not settings_manager.is_dirty
    assert spy.count() == 0
    window.close()


def test_recursive_monitoring(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)

    group_box = QGroupBox("Nested")
    group_box.setObjectName("nestedGroup")
    group_layout = QVBoxLayout(group_box)
    nested_checkbox = QCheckBox("Nested Check")
    nested_checkbox.setObjectName("nestedCheck")
    group_layout.addWidget(nested_checkbox)
    if layout := window.centralWidget().layout():
        layout.addWidget(group_box)

    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()

    assert not settings_manager.is_dirty
    spy = QSignalSpy(settings_manager.dirty_changed)

    nested_checkbox.setChecked(True)
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [True]

    window.close()


def test_load_from_file_marks_clean(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    settings_file = tmp_path / "test_load_file_clean.ini"
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    prep_settings = QSettings(str(settings_file), QSettings.Format.IniFormat)
    prep_settings.setValue(window.checkbox.objectName(), "true")
    prep_settings.sync()
    del prep_settings

    settings_manager.mark_dirty()
    assert settings_manager.is_dirty
    spy = QSignalSpy(settings_manager.dirty_changed)

    settings_manager.load_from_file(str(settings_file))
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert not settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [False]
    window.close()


def test_save_to_file_marks_clean(
    qtbot: QtBot, settings_manager: QtSettingsManager, tmp_path: Path
):
    settings_file = tmp_path / "test_save_file_clean.ini"
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)
    settings_manager.load_state()

    spy = QSignalSpy(settings_manager.dirty_changed)
    window.spin_box.setValue(12)
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)
    assert settings_manager.is_dirty
    assert spy.count() >= 1

    spy_save = QSignalSpy(settings_manager.dirty_changed)
    settings_manager.save_to_file(str(settings_file))
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert not settings_manager.is_dirty
    assert spy_save.count() == 1
    assert spy_save.at(0) == [False]
    window.close()


def test_custom_signal_monitor_registration(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    class MyCustomWidget(QWidget):
        somethingHappened = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._internal_data = "initial"

        def do_something(self, data: str):
            self._internal_data = data
            self.somethingHappened.emit(data)

        def get_data(self):
            return self._internal_data

    class MyCustomHandler:
        @staticmethod
        def save(widget: MyCustomWidget, settings: QSettings):
            settings.setValue(widget.objectName(), widget.get_data())

        @staticmethod
        def load(widget: MyCustomWidget, settings: QSettings):
            value = settings.value(widget.objectName())
            if value is not None:
                widget.do_something(str(value))

    class MyCustomMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: MyCustomWidget) -> list[SignalInstance]:
            return [widget.somethingHappened]

    settings_manager.register_handler(MyCustomWidget, MyCustomHandler)
    settings_manager.register_signal_monitor(MyCustomWidget, MyCustomMonitor)

    window = TestSettingsWindow()
    qtbot.add_widget(window)
    custom_widget = MyCustomWidget()
    custom_widget.setObjectName("myCustom")
    if layout := window.centralWidget().layout():
        layout.addWidget(custom_widget)
    window.show()
    qtbot.waitExposed(window)

    settings_manager.load_state()
    assert not settings_manager.is_dirty

    spy = QSignalSpy(settings_manager.dirty_changed)

    custom_widget.do_something("event data")
    qtbot.waitSignal(settings_manager.dirty_changed, timeout=1000)

    assert settings_manager.is_dirty
    assert spy.count() == 1
    assert spy.at(0) == [True]

    window.close()
