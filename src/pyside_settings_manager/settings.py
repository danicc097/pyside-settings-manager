from __future__ import annotations
import pickle
from typing import (
    Any,
    Optional,
    Type,
    Dict,
    TypeVar,
    Protocol,
    cast,
    runtime_checkable,
    List,
)

from PySide6.QtCore import (
    QSettings,
    QByteArray,
    QObject,
    Qt,
    Signal,
    QSignalBlocker,
    SignalInstance,
)
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


@runtime_checkable
class SignalMonitor(Protocol[T]):
    @staticmethod
    def get_signals_to_monitor(widget: T) -> List[SignalInstance]: ...


@runtime_checkable
class SettingsManager(Protocol):
    """Defines the public interface for settings manager."""

    dirty_changed: Signal

    @property
    def is_dirty(self) -> bool: ...

    def save_state(self, *, custom_data: Optional[dict[str, Any]] = None): ...
    def load_state(self) -> Optional[dict[str, Any]]: ...
    def register_handler(self, widget_type: Type[T], handler: WidgetHandler[T]): ...

    def register_signal_monitor(
        self, widget_type: Type[T], monitor: SignalMonitor[T]
    ): ...
    def save_custom_data(self, key: str, data: Any): ...
    def load_custom_data(self, key: str) -> Optional[Any]: ...
    def skip_widget(self, widget: QObject): ...
    def save_to_file(
        self, filepath: str, *, custom_data: Optional[dict[str, Any]] = None
    ) -> None: ...
    def load_from_file(self, filepath: str) -> Optional[dict[str, Any]]: ...
    def mark_clean(self): ...
    def mark_dirty(self): ...


HandlerRegistry = Dict[Type[QObject], WidgetHandler]
SignalMonitorRegistry = Dict[Type[QObject], SignalMonitor]


def create_settings_manager(qsettings: QSettings) -> SettingsManager:
    """Create a new settings manager instance."""
    return QtSettingsManager(qsettings)


class QtSettingsManager(QObject):
    """
    A Qt settings manager using SignalMonitors for dirty tracking.
    """

    dirty_changed = Signal(bool)

    def __init__(
        self,
        qsettings: QSettings,
    ):
        super().__init__()
        self._settings = qsettings
        self._dirty: bool = False

        self._connected_signals: Dict[QObject, List[SignalInstance]] = {}

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

        self._signal_monitors: SignalMonitorRegistry = {
            QCheckBox: self.CheckBoxSignalMonitor,
            QLineEdit: self.LineEditSignalMonitor,
            QPushButton: self.PushButtonSignalMonitor,
            QComboBox: self.ComboBoxSignalMonitor,
            QSpinBox: self.SpinBoxSignalMonitor,
            QDoubleSpinBox: self.DoubleSpinBoxSignalMonitor,
            QRadioButton: self.RadioButtonSignalMonitor,
            QTextEdit: self.TextEditSignalMonitor,
            QTabWidget: self.TabWidgetSignalMonitor,
            QSlider: self.SliderSignalMonitor,
            # QMainWindow changes (geometry/state) typically don't mark dirty
        }

    @property
    def is_dirty(self) -> bool:
        """Return whether settings have changed since the last save or load."""
        return self._dirty

    def mark_clean(self) -> None:
        """Mark settings as clean (unchanged) and emit signal if state changed."""
        if self._dirty:
            self._dirty = False
            self.dirty_changed.emit(False)

    def mark_dirty(self) -> None:
        """Mark settings as dirty (changed) and emit signal if state changed."""

        if not self._dirty:
            self._dirty = True
            self.dirty_changed.emit(True)

    def _on_widget_changed(self) -> None:
        """Slot connected to monitored widget signals."""

        self.mark_dirty()

    def _perform_save(
        self, settings: QSettings, custom_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Save widget states and custom data, then mark clean."""
        main_window = self._find_main_window()
        if main_window:
            # No signal blocking needed for save
            self._save_widget_recursive(main_window, settings)

        if custom_data:
            self._save_custom_data(settings, "custom_data", custom_data)

        settings.sync()
        self.mark_clean()

    def _perform_load(self, settings: QSettings) -> Optional[dict[str, Any]]:
        """Load widget states, connect signals, mark clean, return custom data."""
        #  prevent duplicates
        self._disconnect_all_widget_signals()

        # 2. Load widget states recursively
        main_window = self._find_main_window()
        if main_window:
            blocker = QSignalBlocker(main_window)  # Block top-level
            try:
                self._load_widget_recursive(main_window, settings)
            finally:
                blocker.unblock()

        if main_window:
            self._connect_signals_recursive(main_window)

        custom_loaded_data = self._load_custom_data(settings, "custom_data")

        self.mark_clean()

        return custom_loaded_data

    def save_state(self, *, custom_data: Optional[dict[str, Any]] = None) -> None:
        """Save state to default settings."""
        self._perform_save(self._settings, custom_data)

    def load_state(self) -> Optional[dict[str, Any]]:
        """Load state from default settings."""
        return self._perform_load(self._settings)

    def save_to_file(
        self, filepath: str, *, custom_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Save state to a specified file."""
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        self._perform_save(file_settings, custom_data)

    def load_from_file(self, filepath: str) -> Optional[dict[str, Any]]:
        """Load state from a specified file."""
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        if file_settings.status() != QSettings.Status.NoError:
            print(
                f"Warning: Could not load settings from {filepath}. Status: {file_settings.status()}. Using default state."
            )
            self._disconnect_all_widget_signals()
            self.mark_clean()
            return None

        return self._perform_load(file_settings)

    def register_handler(self, widget_type: Type[T], handler: WidgetHandler[T]) -> None:
        """Register a custom widget state handler."""
        self._handlers[widget_type] = handler

    def register_signal_monitor(
        self, widget_type: Type[T], monitor: SignalMonitor[T]
    ) -> None:
        """Register a custom signal monitor for a widget type."""
        self._signal_monitors[widget_type] = monitor

    def _save_custom_data(self, settings: QSettings, key: str, data: Any) -> None:
        """Serialize and save arbitrary Python data using pickle."""
        try:
            settings.setValue(key, QByteArray(pickle.dumps(data)))
        except (pickle.PicklingError, TypeError) as e:
            print(f"Error: Could not pickle custom data for key '{key}': {e}")

    def _load_custom_data(self, settings: QSettings, key: str) -> Optional[Any]:
        """Load and deserialize Python data using pickle."""
        value = settings.value(key)
        if value is not None:
            data_bytes = value.data() if isinstance(value, QByteArray) else value
            if isinstance(data_bytes, bytes):
                try:
                    return pickle.loads(data_bytes)
                except pickle.UnpicklingError as e:
                    print(f"Warning: Could not unpickle data for key '{key}': {e}")
                    return None
                except Exception as e:
                    print(f"Warning: Error unpickling data for key '{key}': {e}")
                    return None
            else:
                print(
                    f"Warning: Unexpected type for custom data key '{key}': {type(value)}"
                )
                return None
        return None

    def save_custom_data(self, key: str, data: Any) -> None:
        """Save arbitrary Python data to default settings and mark dirty."""
        self._save_custom_data(self._settings, key, data)
        self.mark_dirty()

    def load_custom_data(self, key: str) -> Optional[Any]:
        """Load arbitrary Python data from default settings."""
        return self._load_custom_data(self._settings, key)

    def _find_main_window(self) -> Optional[QMainWindow]:
        """Find the main application window."""

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return cast(QMainWindow, widget)
        print("Warning: No QMainWindow found among top-level widgets.")
        return None

    def _get_handler(self, widget: QObject) -> Optional[WidgetHandler]:
        """Find the handler for a specific widget instance."""
        for widget_class, handler_instance in self._handlers.items():
            if isinstance(widget, widget_class):
                return handler_instance
        return None

    def _get_monitor(self, widget: QObject) -> Optional[SignalMonitor]:
        """Find the signal monitor for a specific widget instance."""
        for widget_class, monitor_instance in self._signal_monitors.items():
            if isinstance(widget, widget_class):
                return monitor_instance
        return None

    def skip_widget(self, widget: QObject) -> None:
        """Mark a widget to be skipped during save/load and signal connection."""
        widget.setProperty("_skip_settings", True)

        self._disconnect_widget_signals(widget)

    def _should_skip_widget(self, widget: QObject) -> bool:
        """Check if a widget should be skipped."""
        return not widget.objectName() or widget.property("_skip_settings") is True

    def _save_widget_recursive(self, parent: QObject, settings: QSettings) -> None:
        """Recursively find and save widget states."""

        if not self._should_skip_widget(parent):
            handler = self._get_handler(parent)
            if handler:
                handler.save(parent, settings)

        if isinstance(parent, QMainWindow) and parent.centralWidget():
            self._save_widget_recursive(parent.centralWidget(), settings)

        else:
            for child in parent.children():
                if isinstance(child, QObject):
                    self._save_widget_recursive(child, settings)

    def _load_widget_recursive(self, parent: QObject, settings: QSettings) -> None:
        """Recursively find and load widget states."""
        if not self._should_skip_widget(parent):
            handler = self._get_handler(parent)
            if handler:
                handler.load(parent, settings)
                if isinstance(parent, QWidget):
                    parent.update()  # force repaint

        if isinstance(parent, QMainWindow) and parent.centralWidget():
            self._load_widget_recursive(parent.centralWidget(), settings)
        else:
            for child in parent.children():
                if isinstance(child, QObject):
                    self._load_widget_recursive(child, settings)

    def _connect_signals_recursive(self, parent: QObject) -> None:
        """Recursively find and connect widget signals after loading."""

        if not self._should_skip_widget(parent):
            monitor = self._get_monitor(parent)
            if monitor:
                signals_to_connect = monitor.get_signals_to_monitor(parent)
                if signals_to_connect:
                    connected_list = []
                    for signal in signals_to_connect:
                        try:
                            signal.connect(self._on_widget_changed)
                            connected_list.append(signal)
                        except Exception as e:
                            print(
                                f"Warning: Failed to connect signal for {parent.objectName()}: {e}"
                            )
                    if connected_list:
                        self._connected_signals[parent] = connected_list

        if isinstance(parent, QMainWindow) and parent.centralWidget():
            self._connect_signals_recursive(parent.centralWidget())

        else:
            for child in parent.children():
                if isinstance(child, QObject):
                    self._connect_signals_recursive(child)

    def _disconnect_widget_signals(self, widget: QObject) -> None:
        """Disconnect signals for a specific widget."""
        if widget in self._connected_signals:
            for signal in self._connected_signals[widget]:
                try:
                    signal.disconnect(self._on_widget_changed)
                except (TypeError, RuntimeError):
                    pass
            del self._connected_signals[widget]

    def _disconnect_all_widget_signals(self) -> None:
        """Disconnect all currently monitored signals."""

        widgets_to_disconnect = list(self._connected_signals.keys())
        for widget in widgets_to_disconnect:
            self._disconnect_widget_signals(widget)

        self._connected_signals.clear()

    class CheckBoxSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QCheckBox) -> List[SignalInstance]:
            return [widget.toggled]

    class LineEditSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QLineEdit) -> List[SignalInstance]:
            return [widget.textChanged]

    class PushButtonSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QPushButton) -> List[SignalInstance]:
            return [widget.toggled] if widget.isCheckable() else []

    class ComboBoxSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QComboBox) -> List[SignalInstance]:
            return [widget.currentIndexChanged]

    class SpinBoxSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QSpinBox) -> List[SignalInstance]:
            return [widget.valueChanged]

    class DoubleSpinBoxSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QDoubleSpinBox) -> List[SignalInstance]:
            return [widget.valueChanged]

    class RadioButtonSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QRadioButton) -> List[SignalInstance]:
            return [widget.toggled]

    class TextEditSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QTextEdit) -> List[SignalInstance]:
            return [widget.textChanged]

    class TabWidgetSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QTabWidget) -> List[SignalInstance]:
            return [widget.currentChanged]

    class SliderSignalMonitor:
        @staticmethod
        def get_signals_to_monitor(widget: QSlider) -> List[SignalInstance]:
            return [widget.valueChanged]

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
            geometry = settings.value("geometry")

            if isinstance(geometry, (QByteArray, bytes)):
                widget.restoreGeometry(geometry)
            state = settings.value("state")
            if isinstance(state, (QByteArray, bytes)):
                widget.restoreState(state)
            settings.endGroup()

    class CheckBoxHandler:
        @staticmethod
        def save(widget: QCheckBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QCheckBox, settings: QSettings) -> None:
            value = settings.value(widget.objectName())

            if isinstance(value, str):
                widget.setChecked(value.lower() == "true")
            elif value is not None:
                widget.setChecked(bool(value))

    class LineEditHandler:
        @staticmethod
        def save(widget: QLineEdit, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.text())

        @staticmethod
        def load(widget: QLineEdit, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if value is not None:
                widget.setText(str(value))

    class PushButtonHandler:
        @staticmethod
        def save(widget: QPushButton, settings: QSettings) -> None:
            if widget.isCheckable():
                settings.setValue(f"{widget.objectName()}/checked", widget.isChecked())

        @staticmethod
        def load(widget: QPushButton, settings: QSettings) -> None:
            if widget.isCheckable():
                value = settings.value(f"{widget.objectName()}/checked")
                if isinstance(value, str):
                    widget.setChecked(value.lower() == "true")
                elif value is not None:
                    widget.setChecked(bool(value))

    class ComboBoxHandler:
        @staticmethod
        def save(widget: QComboBox, settings: QSettings) -> None:
            settings.setValue(
                f"{widget.objectName()}/currentIndex", widget.currentIndex()
            )

        @staticmethod
        def load(widget: QComboBox, settings: QSettings) -> None:
            value = settings.value(f"{widget.objectName()}/currentIndex")
            if value is not None:
                try:
                    index = int(value)

                    if 0 <= index < widget.count():
                        widget.setCurrentIndex(index)
                    else:
                        print(
                            f"Warning: Saved index {index} out of range for {widget.objectName()}"
                        )
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not parse index '{value}' for {widget.objectName()}"
                    )

    class SpinBoxHandler:
        @staticmethod
        def save(widget: QSpinBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QSpinBox, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if value is not None:
                try:
                    widget.setValue(int(value))
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not parse int value '{value}' for {widget.objectName()}"
                    )

    class DoubleSpinBoxHandler:
        @staticmethod
        def save(widget: QDoubleSpinBox, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QDoubleSpinBox, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if value is not None:
                try:
                    widget.setValue(float(value))
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not parse float value '{value}' for {widget.objectName()}"
                    )

    class RadioButtonHandler:
        @staticmethod
        def save(widget: QRadioButton, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.isChecked())

        @staticmethod
        def load(widget: QRadioButton, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if isinstance(value, str):
                widget.setChecked(value.lower() == "true")
            elif value is not None:
                widget.setChecked(bool(value))

    class TextEditHandler:
        @staticmethod
        def save(widget: QTextEdit, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.toPlainText())

        @staticmethod
        def load(widget: QTextEdit, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if value is not None:
                widget.setPlainText(str(value))

    class TabWidgetHandler:
        @staticmethod
        def save(widget: QTabWidget, settings: QSettings) -> None:
            settings.setValue(
                f"{widget.objectName()}/currentIndex", widget.currentIndex()
            )

        @staticmethod
        def load(widget: QTabWidget, settings: QSettings) -> None:
            value = settings.value(f"{widget.objectName()}/currentIndex")
            if value is not None:
                try:
                    index = int(value)
                    if 0 <= index < widget.count():
                        widget.setCurrentIndex(index)
                    else:
                        print(
                            f"Warning: Saved tab index {index} out of range for {widget.objectName()}"
                        )
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not parse tab index '{value}' for {widget.objectName()}"
                    )

    class SliderHandler:
        @staticmethod
        def save(widget: QSlider, settings: QSettings) -> None:
            settings.setValue(widget.objectName(), widget.value())

        @staticmethod
        def load(widget: QSlider, settings: QSettings) -> None:
            value = settings.value(widget.objectName())
            if value is not None:
                try:
                    widget.setValue(int(value))
                except (ValueError, TypeError):
                    print(
                        f"Warning: Could not parse slider value '{value}' for {widget.objectName()}"
                    )
