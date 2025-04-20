from __future__ import annotations
import pickle
from typing import (
    Any,
    Optional,
    Type,
    Dict,
    Callable,
    TypeVar,
    Generic,
    Protocol,
    cast,
    runtime_checkable,
)
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


@runtime_checkable
class SettingsManager(Protocol):
    """Defines the public interface for settings manager."""

    def save_state(self, *, custom_data: Optional[dict[str, Any]] = None): ...
    def load_state(self) -> Optional[dict[str, Any]]: ...
    def register_handler(self, widget_type: Type[T], handler: WidgetHandler[T]): ...
    def save_custom_data(self, key: str, data: Any): ...
    def load_custom_data(self, key: str) -> Optional[Any]: ...
    def skip_widget(self, widget: QObject): ...
    def save_to_file(
        self, filepath: str, *, custom_data: Optional[dict[str, Any]] = None
    ) -> None: ...
    def load_from_file(self, filepath: str) -> Optional[dict[str, Any]]: ...


def create_settings_manager(qsettings: QSettings) -> SettingsManager:
    """Create a new settings manager instance."""
    return QtSettingsManager(qsettings)


class QtSettingsManager(SettingsManager):
    """A type-safe Qt settings manager with automatic widget state persistence."""

    def __init__(
        self,
        qsettings: QSettings,
    ):
        super().__init__()
        self._settings = qsettings
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
            QSlider: self.SliderHandler,
        }

    def _perform_save(
        self, settings: QSettings, custom_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Save all registered widget states and optional custom data using the provided QSettings."""
        main_window = self._find_main_window()
        if main_window:
            self._save_widget(main_window, settings)
            self._save_children(main_window, settings)

        if custom_data:
            self._save_custom_data(settings, "custom_data", custom_data)

        settings.sync()

    def _perform_load(self, settings: QSettings) -> Optional[dict[str, Any]]:
        """Load all registered widget states using the provided QSettings and return custom data."""
        main_window = self._find_main_window()
        if main_window:
            self._load_widget(main_window, settings)
            self._load_children(main_window, settings)

        return self._load_custom_data(settings, "custom_data")

    def save_state(self, *, custom_data: Optional[dict[str, Any]] = None) -> None:
        """Save all registered widget states and optional custom data to the default settings."""
        self._perform_save(self._settings, custom_data)

    def load_state(self) -> Optional[dict[str, Any]]:
        """Load all registered widget states from the default settings and return any stored custom data."""
        return self._perform_load(self._settings)

    def save_to_file(
        self, filepath: str, *, custom_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Save the current application state to a specified file."""
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        self._perform_save(file_settings, custom_data)

    def load_from_file(self, filepath: str) -> Optional[dict[str, Any]]:
        """Load application state from a specified file."""
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        if file_settings.status() != QSettings.Status.NoError:
            print(
                f"Warning: Could not load settings from {filepath}. Status: {file_settings.status()}"
            )
            raise FileNotFoundError(filepath)

        return self._perform_load(file_settings)

    def register_handler(self, widget_type: Type[T], handler: WidgetHandler[T]) -> None:
        """Register a custom widget handler."""
        self._handlers[widget_type] = handler

    def _save_custom_data(self, settings: QSettings, key: str, data: Any) -> None:
        """Serialize and save arbitrary Python data using pickle to the given QSettings."""
        settings.setValue(key, QByteArray(pickle.dumps(data)))

    def _load_custom_data(self, settings: QSettings, key: str) -> Optional[Any]:
        """Load and deserialize Python data using pickle from the given QSettings."""
        if (value := settings.value(key)) is not None:
            if isinstance(value, QByteArray):
                return pickle.loads(value.data())
            elif isinstance(value, bytes):
                return pickle.loads(value)
            else:
                print(
                    f"Warning: Unexpected type for custom data key '{key}': {type(value)}"
                )
                return None
        return None

    def save_custom_data(self, key: str, data: Any) -> None:
        """Serialize and save arbitrary Python data using pickle to the default settings."""
        self._save_custom_data(self._settings, key, data)

    def load_custom_data(self, key: str) -> Optional[Any]:
        """Load and deserialize Python data using pickle from the default settings."""
        return self._load_custom_data(self._settings, key)

    def _find_main_window(self) -> Optional[QMainWindow]:
        """Find the main application window."""
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return cast(QMainWindow, widget)
        return None

    # --- Pass settings down the recursive calls ---
    def _save_children(self, parent: QObject, settings: QSettings) -> None:
        """Recursively save child widgets with object names using the provided QSettings."""
        if isinstance(parent, QMainWindow) and parent.centralWidget():
            central_widget = parent.centralWidget()
            if hasattr(central_widget, "objectName") and central_widget.objectName():
                self._save_widget(central_widget, settings)
            self._save_children(central_widget, settings)

        for child in parent.children():
            if hasattr(child, "objectName") and child.objectName():
                self._save_widget(child, settings)
            self._save_children(child, settings)

    # --- Pass settings down the recursive calls ---
    def _save_widget(self, widget: QObject, settings: QSettings) -> None:
        """Save individual widget state using registered handler and provided QSettings."""
        if self._should_skip_widget(widget):
            return
        if not widget.objectName():
            return

        handler = None
        for widget_class, handler_class in self._handlers.items():
            if isinstance(widget, widget_class):
                handler = handler_class
                break

        if handler:
            handler.save(widget, settings)

    def _load_children(self, parent: QObject, settings: QSettings) -> None:
        """Recursively load child widgets with object names using the provided QSettings."""
        if isinstance(parent, QMainWindow) and parent.centralWidget():
            central_widget = parent.centralWidget()
            if hasattr(central_widget, "objectName") and central_widget.objectName():
                self._load_widget(central_widget, settings)
            self._load_children(central_widget, settings)

        for child in parent.children():
            if hasattr(child, "objectName") and child.objectName():
                self._load_widget(child, settings)
            self._load_children(child, settings)

    def _load_widget(self, widget: QObject, settings: QSettings) -> None:
        """Load individual widget state using registered handler and provided QSettings."""
        if self._should_skip_widget(widget):
            return
        if not widget.objectName():
            return

        handler = None
        for widget_class, handler_class in self._handlers.items():
            if isinstance(widget, widget_class):
                handler = handler_class
                break

        if handler:
            handler.load(widget, settings)

    def skip_widget(self, widget: QObject) -> None:
        """Mark a widget to be skipped during save/load operations."""
        widget.setProperty("_skip_settings", True)

    def _should_skip_widget(self, widget: QObject) -> bool:
        """Check if a widget should be skipped during save/load operations."""
        return widget.property("_skip_settings") is True

    class MainWindowHandler:
        @staticmethod
        def save(widget: QMainWindow, settings: QSettings) -> None:
            settings.beginGroup(widget.objectName())
            settings.setValue("geometry", widget.saveGeometry())
            settings.setValue("state", widget.saveState())
            settings.endGroup()

        @staticmethod
        def load(widget: QMainWindow, settings: QSettings) -> None:
            settings.beginGroup(widget.objectName())
            if geometry := settings.value("geometry"):
                widget.restoreGeometry(geometry)
            if state := settings.value("state"):
                widget.restoreState(state)
            settings.endGroup()

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

    class SliderHandler:
        @staticmethod
        def save(widget: QSlider, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QSlider, settings: QSettings) -> None:
            if (value := settings.value(widget.objectName())) is not None:
                widget.setValue(int(value))
