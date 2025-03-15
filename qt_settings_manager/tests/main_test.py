import os
import pytest
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QSize
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
from qt_settings_manager import QtSettingsManager


@pytest.fixture(scope="module")
def qapp():
    """Provide QApplication instance for all tests"""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    app.quit()


class TestSettingsWindow(QMainWindow):
    """Test window containing various widgets"""

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

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("testSlider")
        self.slider.setRange(0, 100)

        self.radio_button = QRadioButton("Test Radio Button")
        self.radio_button.setObjectName("testRadioButton")

        self.double_spin_box = QDoubleSpinBox()
        self.double_spin_box.setObjectName("testDoubleSpinBox")

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


@pytest.fixture
def settings_manager(tmp_path: Path) -> QtSettingsManager:
    """Provide a clean settings manager with temp storage"""
    QApplication.setOrganizationName("TestOrg")
    QApplication.setApplicationName("TestApp")

    settings_path = tmp_path / "settings.ini"
    manager = QtSettingsManager("TestOrg", "TestApp", format=QSettings.Format.IniFormat)
    manager._settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    return manager


def test_save_load_main_window(qtbot: QtBot):
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Skipping offscreen test")
    main_window = QMainWindow()
    main_window.setObjectName("mainWindow")
    qtbot.add_widget(main_window)
    main_window.resize(800, 600)
    main_window.show()
    qtbot.waitExposed(main_window)

    manager = QtSettingsManager("TestOrg", "TestApp")
    manager.save_state()

    main_window.resize(640, 480)
    assert main_window.size() == QSize(640, 480)

    manager.load_state()
    assert main_window.size() == QSize(800, 600)


def test_checkbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    window.setObjectName("mainWindow")
    window.resize(800, 600)
    window.show()

    qtbot.add_widget(window)
    qtbot.waitExposed(window)

    window.checkbox.setChecked(True)
    settings_manager.save_state()

    window.checkbox.setChecked(False)
    settings_manager.load_state()

    assert window.checkbox.isChecked() is True
    window.close()


def test_lineedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_text = "Test content"
    window.line_edit.setText(test_text)
    settings_manager.save_state()

    window.line_edit.clear()
    settings_manager.load_state()

    assert window.line_edit.text() == test_text
    window.close()


def test_pushbutton_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    window.push_button.setChecked(True)
    settings_manager.save_state()

    window.push_button.setChecked(False)
    settings_manager.load_state()

    assert window.push_button.isChecked() is True
    window.close()


def test_combobox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_index = 2
    window.combo_box.setCurrentIndex(test_index)
    settings_manager.save_state()

    window.combo_box.setCurrentIndex(0)
    settings_manager.load_state()

    assert window.combo_box.currentIndex() == test_index
    window.close()


def test_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_value = 42
    window.spin_box.setValue(test_value)
    settings_manager.save_state()

    window.spin_box.setValue(0)
    settings_manager.load_state()

    assert window.spin_box.value() == test_value
    window.close()


def test_textedit_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_text = "Multi\nline\ntext"
    window.text_edit.setPlainText(test_text)
    settings_manager.save_state()

    window.text_edit.clear()
    settings_manager.load_state()

    assert window.text_edit.toPlainText() == test_text
    window.close()


def test_radio_button_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    window.radio_button.setChecked(True)
    settings_manager.save_state()

    window.radio_button.setChecked(False)
    settings_manager.load_state()

    assert window.radio_button.isChecked() is True
    window.close()


def test_double_spinbox_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_value = 3.14
    window.double_spin_box.setValue(test_value)
    settings_manager.save_state()

    window.double_spin_box.setValue(0)
    settings_manager.load_state()

    assert window.double_spin_box.value() == test_value
    window.close()


def test_tabwidget_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_index = 1
    window.tab_widget.setCurrentIndex(test_index)
    settings_manager.save_state()

    window.tab_widget.setCurrentIndex(0)
    settings_manager.load_state()

    assert window.tab_widget.currentIndex() == test_index
    window.close()


def test_slider_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    test_value = 75
    window.slider.setValue(test_value)
    settings_manager.save_state()

    window.slider.setValue(0)
    settings_manager.load_state()

    assert window.slider.value() == test_value
    window.close()


def test_custom_data_save_load(qtbot: QtBot, settings_manager: QtSettingsManager):
    test_data = {
        "string": "value",
        "int": 42,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }
    settings_manager.save_custom_data("test_key", test_data)
    loaded_data = settings_manager.load_custom_data("test_key")
    assert loaded_data == test_data


def test_custom_handler_registration(qtbot: QtBot, settings_manager: QtSettingsManager):
    class CustomWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.value = 0

    class CustomHandler:
        @staticmethod
        def save(widget: CustomWidget, settings: QSettings):
            settings.setValue(widget.objectName(), widget.value)

        @staticmethod
        def load(widget: CustomWidget, settings: QSettings):
            if (value := settings.value(widget.objectName())) is not None:
                widget.value = int(value)

    settings_manager.register_handler(CustomWidget, CustomHandler)

    widget = CustomWidget()
    widget.setObjectName("customWidget")
    test_value = 100
    widget.value = test_value

    qtbot.add_widget(widget)
    settings_manager._save_widget(widget)
    widget.value = 0
    settings_manager._load_widget(widget)

    assert widget.value == test_value


def test_ignore_widgets_without_objectname(
    qtbot: QtBot, settings_manager: QtSettingsManager
):
    widget = QCheckBox()
    qtbot.add_widget(widget)
    # Do not set an object name for this widget
    settings_manager._save_widget(widget)
    assert not settings_manager._settings.contains("")


def test_recursive_child_saving(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    parent = QWidget()
    parent.setObjectName("parentWidget")
    child = QCheckBox(parent)
    child.setObjectName("childCheckbox")
    if layout := window.centralWidget().layout():
        layout.addWidget(parent)

    child.setChecked(True)
    settings_manager.save_state()

    child.setChecked(False)
    settings_manager.load_state()

    assert child.isChecked() is True
    window.close()


def test_geometry_restoration(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    original_geometry = window.saveGeometry()
    window.resize(400, 300)
    window.move(50, 50)
    modified_geometry = window.saveGeometry()

    settings_manager.save_state()
    window.restoreGeometry(original_geometry)
    settings_manager.load_state()

    assert window.saveGeometry() == modified_geometry
    window.close()


def test_state_restoration(qtbot: QtBot, settings_manager: QtSettingsManager):
    window = TestSettingsWindow()
    qtbot.add_widget(window)
    window.show()
    qtbot.waitExposed(window)

    original_state = window.saveState()
    window.setWindowState(Qt.WindowState.WindowMaximized)
    modified_state = window.saveState()

    settings_manager.save_state()
    window.restoreState(original_state)
    settings_manager.load_state()

    assert window.saveState() == modified_state
    window.close()


def test_custom_data_versioning(qtbot: QtBot, settings_manager: QtSettingsManager):
    test_data = {"__version__": "1.0", "data": {"value": 42}}
    settings_manager.save_custom_data("versioned_data", test_data)
    loaded_data = settings_manager.load_custom_data("versioned_data")
    assert loaded_data is not None
    assert loaded_data["__version__"] == "1.0"
    assert loaded_data["data"]["value"] == 42
