# settings.py
from __future__ import annotations
import os
import pickle
import logging
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
    Union,
    Set,
)

from PySide6.QtCore import (
    QSettings,
    QByteArray,
    QObject,
    Qt,
    Signal,
    QSignalBlocker,
    SignalInstance,
    QSize,
    QPoint,
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

# Define FLOAT_TOLERANCE
FLOAT_TOLERANCE = 1e-6
logger = logging.getLogger(__name__)


# --- Updated SettingsHandler Protocol ---
@runtime_checkable
class SettingsHandler(Protocol):
    """Protocol defining methods for saving, loading, comparing, and monitoring widgets."""

    def save(self, widget: Any, settings: QSettings) -> None: ...
    def load(self, widget: Any, settings: QSettings) -> None: ...
    def compare(self, widget: Any, settings: QSettings) -> bool: ...
    def get_signals_to_monitor(self, widget: Any) -> List[SignalInstance]: ...


# --- Default Handler Implementations ---
class DefaultCheckBoxHandler:
    def save(self, widget: QCheckBox, settings: QSettings):
        settings.setValue(widget.objectName(), widget.isChecked())

    def load(self, widget: QCheckBox, settings: QSettings):
        value = settings.value(widget.objectName(), widget.isChecked(), type=bool)
        widget.setChecked(cast(bool, value))

    def compare(self, widget: QCheckBox, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: bool = widget.isChecked()
        saved_value = cast(bool, settings.value(key, current_value, type=bool))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QCheckBox) -> List[SignalInstance]:
        return [widget.stateChanged]


class DefaultLineEditHandler:
    def save(self, widget: QLineEdit, settings: QSettings):
        settings.setValue(widget.objectName(), widget.text())

    def load(self, widget: QLineEdit, settings: QSettings):
        value = settings.value(widget.objectName(), widget.text(), type=str)
        widget.setText(cast(str, value))

    def compare(self, widget: QLineEdit, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: str = widget.text()
        saved_value = cast(str, settings.value(key, current_value, type=str))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QLineEdit) -> List[SignalInstance]:
        return [widget.textChanged]


class DefaultPushButtonHandler:
    def save(self, widget: QPushButton, settings: QSettings):
        if widget.isCheckable():
            settings.setValue(widget.objectName(), widget.isChecked())

    def load(self, widget: QPushButton, settings: QSettings):
        if widget.isCheckable():
            value = settings.value(widget.objectName(), widget.isChecked(), type=bool)
            widget.setChecked(cast(bool, value))

    def compare(self, widget: QPushButton, settings: QSettings) -> bool:
        if not widget.isCheckable():
            return False
        key = widget.objectName()
        current_value: bool = widget.isChecked()
        saved_value = cast(bool, settings.value(key, current_value, type=bool))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QPushButton) -> List[SignalInstance]:
        return [widget.toggled] if widget.isCheckable() else []


class DefaultComboBoxHandler:
    def save(self, widget: QComboBox, settings: QSettings):
        key = widget.objectName()
        settings.setValue(f"{key}/currentIndex", widget.currentIndex())
        if widget.isEditable():
            settings.setValue(f"{key}/currentText", widget.currentText())

    def load(self, widget: QComboBox, settings: QSettings):
        key = widget.objectName()
        index = settings.value(f"{key}/currentIndex", widget.currentIndex(), type=int)
        index = cast(int, index)
        if 0 <= index < widget.count():
            widget.setCurrentIndex(index)
        elif widget.count() > 0:
            widget.setCurrentIndex(0)  # Default to 0 if saved index invalid
        if widget.isEditable():
            text = settings.value(f"{key}/currentText", widget.currentText(), type=str)
            text = cast(str, text)
            widget.setCurrentText(text)

    def compare(self, widget: QComboBox, settings: QSettings) -> bool:
        key = widget.objectName()
        current_index: int = widget.currentIndex()
        saved_index = cast(
            int, settings.value(f"{key}/currentIndex", current_index, type=int)
        )
        changed = current_index != saved_index
        if not changed and widget.isEditable():
            current_text: str = widget.currentText()
            saved_text = cast(
                str,
                settings.value(f"{key}/currentText", current_text, type=str),
            )
            changed = current_text != saved_text
        return changed

    def get_signals_to_monitor(self, widget: QComboBox) -> List[SignalInstance]:
        signals = [widget.currentIndexChanged]
        if widget.isEditable():
            signals.append(widget.currentTextChanged)
        return signals


class DefaultSpinBoxHandler:
    def save(self, widget: QSpinBox, settings: QSettings):
        settings.setValue(widget.objectName(), widget.value())

    def load(self, widget: QSpinBox, settings: QSettings):
        value = settings.value(widget.objectName(), widget.value(), type=int)
        widget.setValue(cast(int, value))

    def compare(self, widget: QSpinBox, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: int = widget.value()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QSpinBox) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultDoubleSpinBoxHandler:
    def save(self, widget: QDoubleSpinBox, settings: QSettings):
        settings.setValue(widget.objectName(), widget.value())

    def load(self, widget: QDoubleSpinBox, settings: QSettings):
        value = settings.value(widget.objectName(), widget.value(), type=float)
        widget.setValue(cast(float, value))

    def compare(self, widget: QDoubleSpinBox, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: float = widget.value()
        saved_value = cast(float, settings.value(key, current_value, type=float))
        changed = abs(current_value - saved_value) > FLOAT_TOLERANCE
        return changed

    def get_signals_to_monitor(self, widget: QDoubleSpinBox) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultRadioButtonHandler:
    def save(self, widget: QRadioButton, settings: QSettings):
        settings.setValue(widget.objectName(), widget.isChecked())

    def load(self, widget: QRadioButton, settings: QSettings):
        key = widget.objectName()
        if settings.contains(key):
            value = settings.value(key, widget.isChecked(), type=bool)
            widget.setChecked(cast(bool, value))

    def compare(self, widget: QRadioButton, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: bool = widget.isChecked()
        if settings.contains(key):
            saved_value = cast(bool, settings.value(key, type=bool))
            return current_value != saved_value
        else:
            return current_value  # Different if True and not saved

    def get_signals_to_monitor(self, widget: QRadioButton) -> List[SignalInstance]:
        return [widget.toggled]


class DefaultTextEditHandler:
    def save(self, widget: QTextEdit, settings: QSettings):
        settings.setValue(widget.objectName(), widget.toPlainText())

    def load(self, widget: QTextEdit, settings: QSettings):
        value = settings.value(widget.objectName(), widget.toPlainText(), type=str)
        widget.setPlainText(cast(str, value))

    def compare(self, widget: QTextEdit, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: str = widget.toPlainText()
        saved_value = cast(str, settings.value(key, current_value, type=str))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QTextEdit) -> List[SignalInstance]:
        return [widget.textChanged]


class DefaultTabWidgetHandler:
    def save(self, widget: QTabWidget, settings: QSettings):
        settings.setValue(widget.objectName(), widget.currentIndex())

    def load(self, widget: QTabWidget, settings: QSettings):
        index = settings.value(widget.objectName(), widget.currentIndex(), type=int)
        index = cast(int, index)
        if 0 <= index < widget.count():
            widget.setCurrentIndex(index)

    def compare(self, widget: QTabWidget, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: int = widget.currentIndex()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QTabWidget) -> List[SignalInstance]:
        return [widget.currentChanged]


class DefaultSliderHandler:
    def save(self, widget: QSlider, settings: QSettings):
        settings.setValue(widget.objectName(), widget.value())

    def load(self, widget: QSlider, settings: QSettings):
        value = settings.value(widget.objectName(), widget.value(), type=int)
        value = cast(int, value)
        if widget.minimum() <= value <= widget.maximum():
            widget.setValue(value)
        else:
            logger.warning(
                f"Loaded value {value} for slider {widget.objectName()} is out of range ({widget.minimum()}-{widget.maximum()}). Using default."
            )
            widget.setValue(widget.value())

    def compare(self, widget: QSlider, settings: QSettings) -> bool:
        key = widget.objectName()
        current_value: int = widget.value()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QSlider) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultMainWindowHandler:
    def save(self, widget: QMainWindow, settings: QSettings):
        key = widget.objectName() or "MainWindow"
        settings.beginGroup(key)
        settings.setValue("geometry", widget.saveGeometry())
        settings.setValue("state", widget.saveState())
        settings.endGroup()

    def load(self, widget: QMainWindow, settings: QSettings):
        key = widget.objectName() or "MainWindow"
        settings.beginGroup(key)
        geometry = settings.value("geometry", type=QByteArray)
        if isinstance(geometry, (QByteArray, bytes)):
            widget.restoreGeometry(geometry)
        state = settings.value("state", type=QByteArray)
        if isinstance(state, (QByteArray, bytes)):
            widget.restoreState(state)
        settings.endGroup()

    def compare(self, widget: QMainWindow, settings: QSettings) -> bool:
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            logger.debug(
                "Skipping QMainWindow geometry/state comparison in offscreen mode."
            )
            return False

        key = widget.objectName() or "MainWindow"
        settings.beginGroup(key)
        current_geometry = widget.saveGeometry()
        saved_geometry = settings.value("geometry", type=QByteArray)
        geometry_differs = current_geometry != saved_geometry
        current_state = widget.saveState()
        saved_state = settings.value("state", type=QByteArray)
        state_differs = current_state != saved_state
        settings.endGroup()
        if geometry_differs:
            return True
        if state_differs:
            return True
        return False

    def get_signals_to_monitor(self, widget: QMainWindow) -> List[SignalInstance]:
        return []


# --- Settings Manager Protocol (Adjusted) ---
@runtime_checkable
class SettingsManager(Protocol):
    """Defines the public interface for settings manager."""

    touched_changed: SignalInstance

    @property
    def is_touched(self) -> bool: ...
    def save_state(self) -> None: ...
    def load_state(self) -> None: ...
    def register_handler(
        self, widget_type: Any, handler_instance: SettingsHandler
    ) -> None: ...
    def save_custom_data(self, key: str, data: Any) -> None: ...
    def load_custom_data(self, key: str) -> Optional[Any]: ...
    def skip_widget(self, widget: QWidget) -> None: ...
    def unskip_widget(self, widget: QWidget) -> None: ...
    def save_to_file(self, filepath: str) -> None: ...
    def load_from_file(self, filepath: str) -> None: ...
    def mark_untouched(self) -> None: ...
    def mark_touched(self) -> None: ...
    def has_unsaved_changes(
        self, source: Optional[Union[str, QSettings]] = None
    ) -> bool: ...
    def get_managed_widgets(self) -> List[QWidget]: ...


HandlerRegistry = Dict[Type[Any], SettingsHandler]


def create_settings_manager(qsettings: QSettings) -> SettingsManager:
    """Create a new settings manager instance."""
    return QtSettingsManager(qsettings)


class QtSettingsManager(QObject):
    """
    A Qt settings manager using unified handlers and providing state comparison.
    """

    touched_changed = Signal(bool)

    def __init__(self, qsettings: QSettings):
        super().__init__()
        self._settings = qsettings
        self._touched: bool = False
        self._connected_signals: Dict[QWidget, List[SignalInstance]] = {}
        self._skipped_widgets: Set[QWidget] = set()

        # This dictionary definition is now compatible with the HandlerRegistry type hint
        self._handlers: HandlerRegistry = {
            QMainWindow: DefaultMainWindowHandler(),
            QCheckBox: DefaultCheckBoxHandler(),
            QLineEdit: DefaultLineEditHandler(),
            QPushButton: DefaultPushButtonHandler(),
            QComboBox: DefaultComboBoxHandler(),
            QSpinBox: DefaultSpinBoxHandler(),
            QDoubleSpinBox: DefaultDoubleSpinBoxHandler(),
            QRadioButton: DefaultRadioButtonHandler(),
            QTextEdit: DefaultTextEditHandler(),
            QTabWidget: DefaultTabWidgetHandler(),
            QSlider: DefaultSliderHandler(),
        }

    @property
    def is_touched(self) -> bool:
        return self._touched

    def mark_untouched(self) -> None:
        if self._touched:
            self._touched = False
            self.touched_changed.emit(False)

    def mark_touched(self) -> None:
        if not self._touched:
            self._touched = True
            self.touched_changed.emit(True)

    def _on_widget_changed(self) -> None:
        sender = self.sender()
        if isinstance(sender, QWidget) and not self._should_skip_widget(sender):
            self.mark_touched()

    def _perform_save(self, settings: QSettings) -> None:
        main_window = self._find_main_window()
        if main_window:
            self._save_widget(main_window, settings)
        else:
            logger.warning("Could not find main window to initiate save.")
        settings.sync()
        if settings.status() != QSettings.Status.NoError:
            logger.error(f"Error syncing settings during save: {settings.status()}")
        self.mark_untouched()

    def _perform_load(self, settings: QSettings) -> None:
        self._disconnect_all_widget_signals()
        main_window = self._find_main_window()
        if main_window:
            blocker = QSignalBlocker(main_window)
            try:
                self._load_widget(main_window, settings)
            except Exception as e:
                logger.error(f"Error during recursive load: {e}", exc_info=True)
            finally:
                blocker.unblock()
            self._connect_signals(main_window)
        else:
            logger.warning("Could not find main window for load/signal connection.")
        self.mark_untouched()

    def save_state(self) -> None:
        logger.info("Saving state to default settings.")
        self._perform_save(self._settings)

    def load_state(self) -> None:
        logger.info("Loading state from default settings.")
        self._perform_load(self._settings)

    def save_to_file(self, filepath: str) -> None:
        logger.info(f"Saving state to file: {filepath}")
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        self._perform_save(file_settings)

    def load_from_file(self, filepath: str) -> None:
        logger.info(f"Loading state from file: {filepath}")
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        if file_settings.status() != QSettings.Status.NoError:
            logger.warning(
                f"Could not load settings from {filepath}. Status: {file_settings.status()}. State unchanged."
            )
            self._disconnect_all_widget_signals()
            self.mark_untouched()
            return
        self._perform_load(file_settings)

    def register_handler(
        self, widget_type: Type[QWidget], handler_instance: SettingsHandler
    ) -> None:
        if not isinstance(handler_instance, SettingsHandler):
            raise TypeError("Handler must conform to SettingsHandler protocol.")
        logger.debug(f"Registering handler for type {widget_type.__name__}")
        self._handlers[widget_type] = handler_instance

    def _save_custom_data_impl(self, settings: QSettings, key: str, data: Any) -> None:
        try:
            pickled_data = pickle.dumps(data)
            settings.setValue(f"customData/{key}", QByteArray(pickled_data))
        except (pickle.PicklingError, TypeError, AttributeError) as e:
            logger.error(
                f"Could not pickle custom data for key '{key}': {e}", exc_info=True
            )

    def _load_custom_data_impl(self, settings: QSettings, key: str) -> Optional[Any]:
        settings_key = f"customData/{key}"
        value = settings.value(settings_key)
        if value is not None:
            data_bytes = value if isinstance(value, bytes) else bytes(value)
            if isinstance(data_bytes, bytes) and data_bytes:
                try:
                    return pickle.loads(data_bytes)
                except pickle.UnpicklingError as e:
                    logger.warning(f"Could not unpickle data for key '{key}': {e}")
                except Exception as e:
                    logger.error(
                        f"Error unpickling data for key '{key}': {e}", exc_info=True
                    )
            else:
                logger.warning(
                    f"No valid data found for custom data key '{key}' (type: {type(value)})"
                )
        return None

    def save_custom_data(self, key: str, data: Any) -> None:
        self._save_custom_data_impl(self._settings, key, data)
        self._settings.sync()
        self.mark_touched()

    def load_custom_data(self, key: str) -> Optional[Any]:
        return self._load_custom_data_impl(self._settings, key)

    def _find_main_window(self) -> Optional[QMainWindow]:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return cast(QMainWindow, widget)
        logger.warning("No QMainWindow found among top-level widgets.")
        return None

    def _get_handler(self, widget: QWidget) -> Optional[SettingsHandler]:
        widget_class = type(widget)
        if widget_class in self._handlers:
            return self._handlers[widget_class]
        for base_class in widget_class.__mro__[1:]:
            if base_class in self._handlers:
                return self._handlers[base_class]
        return None

    def skip_widget(self, widget: QWidget) -> None:
        if widget not in self._skipped_widgets:
            logger.debug(
                f"Skipping widget: {widget.objectName()} ({type(widget).__name__})"
            )
            self._skipped_widgets.add(widget)
            self._disconnect_widget_signals(widget)

    def unskip_widget(self, widget: QWidget) -> None:
        if widget in self._skipped_widgets:
            logger.debug(
                f"Unskipping widget: {widget.objectName()} ({type(widget).__name__})"
            )
            self._skipped_widgets.remove(widget)
            if not self._should_skip_widget(widget):
                handler = self._get_handler(widget)
                if handler:
                    self._connect_widget_signals(widget, handler)

    def _should_skip_widget(self, widget: QWidget) -> bool:
        return not widget.objectName() or widget in self._skipped_widgets

    # --- REFINED Recursive Methods ---
    def _process_widget_and_recurse(
        self,
        parent: QWidget,
        settings: Optional[QSettings],
        operation: str,
        managed_list: Optional[List[QWidget]] = None,
    ) -> bool:
        if self._should_skip_widget(parent):
            return False

        exact_handler = self._handlers.get(type(parent))
        handler_to_use = exact_handler or self._get_handler(parent)

        if handler_to_use:
            try:
                if operation == "save" and settings:
                    handler_to_use.save(parent, settings)
                elif operation == "load" and settings:
                    handler_to_use.load(parent, settings)
                    parent.updateGeometry()
                    parent.update()
                elif operation == "connect":
                    self._connect_widget_signals(parent, handler_to_use)
                elif operation == "compare" and settings:
                    if handler_to_use.compare(parent, settings):
                        logger.info(
                            f"Difference found in widget: {parent.objectName()} ({type(parent).__name__})"
                        )
                        return True
                elif operation == "collect" and managed_list is not None:
                    managed_list.append(parent)
            except Exception as e:
                logger.error(
                    f"Error during '{operation}' on widget {parent.objectName()} ({type(parent).__name__}): {e}",
                    exc_info=True,
                )
                if operation == "compare":
                    return True

        is_known_container = isinstance(parent, (QMainWindow, QGroupBox))
        should_recurse = is_known_container or (exact_handler is None)

        if should_recurse:
            if isinstance(parent, QMainWindow) and parent.centralWidget():
                if self._process_widget_and_recurse(
                    parent.centralWidget(), settings, operation, managed_list
                ):
                    return True
            else:
                child: QWidget
                for child in parent.findChildren(
                    QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
                ):
                    if self._process_widget_and_recurse(
                        child, settings, operation, managed_list
                    ):
                        return True
        return False

    def _save_widget(self, parent: QWidget, settings: QSettings) -> None:
        self._process_widget_and_recurse(parent, settings, "save")

    def _load_widget(self, parent: QWidget, settings: QSettings) -> None:
        self._process_widget_and_recurse(parent, settings, "load")

    def _connect_signals(self, parent: QWidget) -> None:
        self._process_widget_and_recurse(parent, None, "connect")

    def _compare_widget(self, parent: QWidget, settings: QSettings) -> bool:
        return self._process_widget_and_recurse(parent, settings, "compare")

    def _collect_managed_widgets(
        self, parent: QWidget, managed_list: List[QWidget]
    ) -> None:
        self._process_widget_and_recurse(parent, None, "collect", managed_list)

    # --- End of REFINED Recursive Methods ---

    def _connect_widget_signals(
        self, widget: QWidget, handler: SettingsHandler
    ) -> None:
        if widget in self._connected_signals:
            return
        if self._should_skip_widget(widget):
            return

        try:
            signals_to_connect = handler.get_signals_to_monitor(widget)
            if signals_to_connect:
                connected_list = []
                for signal in signals_to_connect:
                    try:
                        if isinstance(signal, SignalInstance) and hasattr(
                            signal, "connect"
                        ):
                            signal.connect(self._on_widget_changed)
                            connected_list.append(signal)
                        else:
                            logger.warning(
                                f"Invalid signal object for {widget.objectName()}: {signal}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to connect signal {getattr(signal, 'signal', signal)} for {widget.objectName()}: {e}"
                        )
                if connected_list:
                    self._connected_signals[widget] = connected_list
        except Exception as e:
            logger.error(
                f"Error getting signals for widget {widget.objectName()} ({type(widget).__name__}): {e}",
                exc_info=True,
            )

    def _disconnect_widget_signals(self, widget: QWidget) -> None:
        if widget in self._connected_signals:
            for signal in self._connected_signals[widget]:
                try:
                    signal.disconnect(self._on_widget_changed)
                except (TypeError, RuntimeError):
                    pass
            del self._connected_signals[widget]

    def _disconnect_all_widget_signals(self) -> None:
        logger.debug("Disconnecting all widget signals.")
        widgets_to_disconnect = list(self._connected_signals.keys())
        for widget in widgets_to_disconnect:
            self._disconnect_widget_signals(widget)
        self._connected_signals.clear()

    # --- Public API Methods ---
    def has_unsaved_changes(
        self, source: Optional[Union[str, QSettings]] = None
    ) -> bool:
        settings: Optional[QSettings] = None
        temp_settings = False
        if source is None:
            settings = self._settings
            logger.debug("Comparing against default settings.")
        elif isinstance(source, str):
            logger.debug(f"Comparing against settings file: {source}")
            settings = QSettings(source, QSettings.Format.IniFormat)
            temp_settings = True
            if settings.status() != QSettings.Status.NoError:
                logger.warning(
                    f"Cannot compare: Failed to load settings from {source}. Status: {settings.status()}"
                )
                return False
        elif isinstance(source, QSettings):
            settings = source
            logger.debug("Comparing against provided QSettings object.")
        else:
            raise TypeError(
                "Source must be None, a filepath string, or a QSettings object."
            )

        main_window = self._find_main_window()
        if not main_window:
            logger.warning("Cannot compare: Main window not found.")
            return False

        try:
            is_different = self._compare_widget(main_window, settings)
        finally:
            if temp_settings:
                del settings

        logger.info(f"Comparison result: {'Different' if is_different else 'Same'}")
        return is_different

    def get_managed_widgets(self) -> List[QWidget]:
        managed_widgets: List[QWidget] = []
        main_window = self._find_main_window()
        if main_window:
            self._collect_managed_widgets(main_window, managed_widgets)
        return managed_widgets
