from __future__ import annotations
import pickle
from typing import Any, Optional, Type, Dict, Callable, TypeVar, Generic, Protocol, cast
from PySide6.QtCore import QSettings, QByteArray, QObject, Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QRadioButton,
    QTextEdit,
    QTabWidget,
    QGroupBox,
    QSlider,
)

T = TypeVar("T", bound=QObject, contravariant=True)


class WidgetHandler(Protocol[T]):
    @staticmethod
    def save(widget: T, settings: QSettings) -> None: ...
    @staticmethod
    def load(widget: T, settings: QSettings) -> None: ...


HandlerRegistry = Dict[Type[QObject], WidgetHandler]


class QtSettingsManager(QObject):
    """A type-safe Qt settings manager with automatic widget state persistence."""

    def __init__(
        self,
        organization: str,
        application: str,
        format: QSettings.Format = QSettings.Format.IniFormat,
    ):
        super().__init__()
        QSettings.setDefaultFormat(format)
        self._settings = QSettings(organization, application)
        self._handlers: HandlerRegistry = {
            QMainWindow: self.MainWindowHandler,
            QCheckBox: self.CheckBoxHandler,
            QLineEdit: self.LineEditHandler,
            QPushButton: self.PushButtonHandler,
            QComboBox: self.ComboBoxHandler,
            QSpinBox: self.SpinBoxHandler,
            QDoubleSpinBox: self.DoubleSpinBoxHandler,
            QRadioButton: self.RadioButtonHandler,
            QTextEdit: self.TextEditHandler,
            QTabWidget: self.TabWidgetHandler,
            QGroupBox: self.GroupBoxHandler,
            QSlider: self.SliderHandler,
        }

    def save_state(self, *, custom_data: Optional[dict[str, Any]] = None) -> None:
        """Save all registered widget states and optional custom data."""
        main_window = self._find_main_window()
        if main_window:
            self._save_widget(main_window)
            self._save_children(main_window)

        if custom_data:
            self.save_custom_data("custom_data", custom_data)

        self._settings.sync()

    def load_state(self) -> Optional[dict[str, Any]]:
        """Load all registered widget states and return any stored custom data."""
        main_window = self._find_main_window()
        if main_window:
            self._load_widget(main_window)
            self._load_children(main_window)

        return self.load_custom_data("custom_data")

    def register_handler(self, widget_type: Type[T], handler: WidgetHandler[T]) -> None:
        """Register a custom widget handler."""
        self._handlers[widget_type] = handler

    def save_custom_data(self, key: str, data: Any) -> None:
        """Serialize and save arbitrary Python data using pickle."""
        self._settings.setValue(key, QByteArray(pickle.dumps(data)))

    def load_custom_data(self, key: str) -> Optional[Any]:
        """Load and deserialize Python data using pickle."""
        if (value := self._settings.value(key)) is not None:
            return pickle.loads(bytes(value))
        return None

    def _find_main_window(self) -> Optional[QMainWindow]:
        """Find the main application window."""
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return cast(QMainWindow, widget)

        return None

    def _save_children(self, parent: QObject) -> None:
        """Recursively save child widgets with object names."""
        if isinstance(parent, QMainWindow) and parent.centralWidget():
            central_widget = parent.centralWidget()
            if hasattr(central_widget, "objectName") and central_widget.objectName():
                self._save_widget(central_widget)
            self._save_children(central_widget)

        # direct children (!= central widget)
        for child in parent.children():
            if hasattr(child, "objectName") and child.objectName():
                self._save_widget(child)

            self._save_children(child)

    def _save_widget(self, widget: QObject) -> None:
        """Save individual widget state using registered handler."""
        handler = None
        for widget_class, handler_class in self._handlers.items():
            if isinstance(widget, widget_class):
                handler = handler_class
                break

        if handler:
            handler.save(widget, self._settings)

    def _load_children(self, parent: QObject) -> None:
        """Recursively load child widgets with object names."""
        if isinstance(parent, QMainWindow) and parent.centralWidget():
            central_widget = parent.centralWidget()
            if hasattr(central_widget, "objectName") and central_widget.objectName():
                self._load_widget(central_widget)
            self._load_children(central_widget)

        # direct children (!= central widget)
        for child in parent.children():
            if hasattr(child, "objectName") and child.objectName():
                self._load_widget(child)
            self._load_children(child)

    def _load_widget(self, widget: QObject) -> None:
        """Load individual widget state using registered handler."""

        handler = None
        for widget_class, handler_class in self._handlers.items():
            if isinstance(widget, widget_class):
                handler = handler_class
                break

        if handler:
            handler.load(widget, self._settings)

    class MainWindowHandler:
        @staticmethod
        def save(widget: QMainWindow, settings: QSettings) -> None:
            settings.setValue(f"{widget.objectName()}/geometry", widget.saveGeometry())
            settings.setValue(f"{widget.objectName()}/state", widget.saveState())

        @staticmethod
        def load(widget: QMainWindow, settings: QSettings) -> None:
            if geometry := settings.value(f"{widget.objectName()}/geometry"):
                widget.restoreGeometry(geometry)
            if state := settings.value(f"{widget.objectName()}/state"):
                widget.restoreState(state)

    class CheckBoxHandler:
        @staticmethod
        def save(widget: QCheckBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QCheckBox, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setChecked(bool(value))

    class LineEditHandler:
        @staticmethod
        def save(widget: QLineEdit, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.text())

        @staticmethod
        def load(widget: QLineEdit, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setText(str(value))

    class PushButtonHandler:
        @staticmethod
        def save(widget: QPushButton, settings: QSettings) -> None:
            if widget.isCheckable():
                settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QPushButton, settings: QSettings) -> None:
            if (
                widget.isCheckable()
                and (value := settings.value(widget.objectName())) is not None
            ):
                widget.setChecked(bool(value))

    class ComboBoxHandler:
        @staticmethod
        def save(widget: QComboBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.currentIndex())

        @staticmethod
        def load(widget: QComboBox, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setCurrentIndex(int(value))

    class SpinBoxHandler:
        @staticmethod
        def save(widget: QSpinBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QSpinBox, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setValue(int(value))

    class DoubleSpinBoxHandler:
        @staticmethod
        def save(widget: QDoubleSpinBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QDoubleSpinBox, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setValue(float(value))

    class RadioButtonHandler:
        @staticmethod
        def save(widget: QRadioButton, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QRadioButton, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setChecked(bool(value))

    class TextEditHandler:
        @staticmethod
        def save(widget: QTextEdit, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.toPlainText())

        @staticmethod
        def load(widget: QTextEdit, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setPlainText(str(value))

    class TabWidgetHandler:
        @staticmethod
        def save(widget: QTabWidget, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.currentIndex())

        @staticmethod
        def load(widget: QTabWidget, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setCurrentIndex(int(value))

    class GroupBoxHandler:
        @staticmethod
        def save(widget: QGroupBox, settings: QSettings) -> None:
            if widget.isCheckable():
                settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QGroupBox, settings: QSettings) -> None:
            if (
                widget.isCheckable()
                and (value := settings.value(widget.objectName())) is not None
            ):
                widget.setChecked(bool(value))

    class SliderHandler:
        @staticmethod
        def save(widget: QSlider, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QSlider, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setValue(int(value))
