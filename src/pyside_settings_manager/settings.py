from __future__ import annotations
from enum import Enum
import os
import pickle
import logging
from typing import (
    Any,
    Optional,
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
    QSlider,
)

# Define FLOAT_TOLERANCE
FLOAT_TOLERANCE = 1e-6
logger = logging.getLogger(__name__)

T = TypeVar("T")


# --- Updated SettingsHandler Protocol ---
@runtime_checkable
class SettingsHandler(Protocol):
    """Protocol defining methods for saving, loading, comparing, and monitoring widgets."""

    def save(self, widget: Any, settings: QSettings) -> None: ...
    def load(self, widget: Any, settings: QSettings) -> None: ...
    def compare(self, widget: Any, settings: QSettings) -> bool: ...
    def get_signals_to_monitor(self, widget: Any) -> List[SignalInstance]: ...


SETTINGS_PROPERTY = "settings"
CUSTOM_DATA_GROUP = "customData"


# --- Default Handler Implementations ---
class DefaultCheckBoxHandler:
    def save(self, widget: QCheckBox, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.isChecked())

    def load(self, widget: QCheckBox, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.isChecked(), type=bool
        )
        widget.setChecked(cast(bool, value))

    def compare(self, widget: QCheckBox, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: bool = widget.isChecked()
        saved_value = cast(bool, settings.value(key, current_value, type=bool))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QCheckBox) -> List[SignalInstance]:
        return [widget.stateChanged]


class DefaultLineEditHandler:
    def save(self, widget: QLineEdit, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.text())

    def load(self, widget: QLineEdit, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.text(), type=str
        )
        widget.setText(cast(str, value))

    def compare(self, widget: QLineEdit, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: str = widget.text()
        saved_value = cast(str, settings.value(key, current_value, type=str))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QLineEdit) -> List[SignalInstance]:
        return [widget.textChanged]


class DefaultPushButtonHandler:
    def save(self, widget: QPushButton, settings: QSettings):
        if widget.isCheckable():
            settings.setValue(widget.property(SETTINGS_PROPERTY), widget.isChecked())

    def load(self, widget: QPushButton, settings: QSettings):
        if widget.isCheckable():
            value = settings.value(
                widget.property(SETTINGS_PROPERTY), widget.isChecked(), type=bool
            )
            widget.setChecked(cast(bool, value))

    def compare(self, widget: QPushButton, settings: QSettings) -> bool:
        if not widget.isCheckable():
            return False
        key = widget.property(SETTINGS_PROPERTY)
        current_value: bool = widget.isChecked()
        saved_value = cast(bool, settings.value(key, current_value, type=bool))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QPushButton) -> List[SignalInstance]:
        return [widget.toggled] if widget.isCheckable() else []


class DefaultComboBoxHandler:
    def save(self, widget: QComboBox, settings: QSettings):
        key = widget.property(SETTINGS_PROPERTY)
        settings.setValue(f"{key}/currentIndex", widget.currentIndex())
        if widget.isEditable():
            settings.setValue(f"{key}/currentText", widget.currentText())

    def load(self, widget: QComboBox, settings: QSettings):
        key = widget.property(SETTINGS_PROPERTY)
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
        key = widget.property(SETTINGS_PROPERTY)
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
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.value())

    def load(self, widget: QSpinBox, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.value(), type=int
        )
        widget.setValue(cast(int, value))

    def compare(self, widget: QSpinBox, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: int = widget.value()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QSpinBox) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultDoubleSpinBoxHandler:
    def save(self, widget: QDoubleSpinBox, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.value())

    def load(self, widget: QDoubleSpinBox, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.value(), type=float
        )
        widget.setValue(cast(float, value))

    def compare(self, widget: QDoubleSpinBox, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: float = widget.value()
        saved_value = cast(float, settings.value(key, current_value, type=float))
        changed = abs(current_value - saved_value) > FLOAT_TOLERANCE
        return changed

    def get_signals_to_monitor(self, widget: QDoubleSpinBox) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultRadioButtonHandler:
    def save(self, widget: QRadioButton, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.isChecked())

    def load(self, widget: QRadioButton, settings: QSettings):
        key = widget.property(SETTINGS_PROPERTY)
        if settings.contains(key):
            value = settings.value(key, widget.isChecked(), type=bool)
            widget.setChecked(cast(bool, value))

    def compare(self, widget: QRadioButton, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: bool = widget.isChecked()
        saved_value = cast(bool, settings.value(key, type=bool))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QRadioButton) -> List[SignalInstance]:
        return [widget.toggled]


class DefaultTextEditHandler:
    def save(self, widget: QTextEdit, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.toPlainText())

    def load(self, widget: QTextEdit, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.toPlainText(), type=str
        )
        widget.setPlainText(cast(str, value))

    def compare(self, widget: QTextEdit, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: str = widget.toPlainText()
        saved_value = cast(str, settings.value(key, current_value, type=str))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QTextEdit) -> List[SignalInstance]:
        return [widget.textChanged]


class DefaultTabWidgetHandler:
    def save(self, widget: QTabWidget, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.currentIndex())

    def load(self, widget: QTabWidget, settings: QSettings):
        index = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.currentIndex(), type=int
        )
        index = cast(int, index)
        if 0 <= index < widget.count():
            widget.setCurrentIndex(index)

    def compare(self, widget: QTabWidget, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: int = widget.currentIndex()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QTabWidget) -> List[SignalInstance]:
        return [widget.currentChanged]


class DefaultSliderHandler:
    def save(self, widget: QSlider, settings: QSettings):
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.value())

    def load(self, widget: QSlider, settings: QSettings):
        value = settings.value(
            widget.property(SETTINGS_PROPERTY), widget.value(), type=int
        )
        value = cast(int, value)
        if widget.minimum() <= value <= widget.maximum():
            widget.setValue(value)
        else:
            logger.warning(
                f"Loaded value {value} for slider {widget.property(SETTINGS_PROPERTY)} is out of range ({widget.minimum()}-{widget.maximum()}). Using default."
            )
            widget.setValue(widget.value())

    def compare(self, widget: QSlider, settings: QSettings) -> bool:
        key = widget.property(SETTINGS_PROPERTY)
        current_value: int = widget.value()
        saved_value = cast(int, settings.value(key, current_value, type=int))
        return current_value != saved_value

    def get_signals_to_monitor(self, widget: QSlider) -> List[SignalInstance]:
        return [widget.valueChanged]


class DefaultMainWindowHandler:  # pragma: no cover # off-screen
    def save(self, widget: QMainWindow, settings: QSettings):
        key = widget.property(SETTINGS_PROPERTY) or "MainWindow"
        settings.beginGroup(key)
        settings.setValue("geometry", widget.saveGeometry())
        settings.setValue("state", widget.saveState())
        settings.endGroup()

    def load(self, widget: QMainWindow, settings: QSettings):
        key = widget.property(SETTINGS_PROPERTY) or "MainWindow"
        settings.beginGroup(key)
        geometry = settings.value("geometry", type=QByteArray)
        if isinstance(geometry, (QByteArray, bytes)):
            widget.restoreGeometry(geometry)
        state = settings.value("state", type=QByteArray)
        if isinstance(state, (QByteArray, bytes)):
            widget.restoreState(state)
        settings.endGroup()

    def compare(self, widget: QMainWindow, settings: QSettings) -> bool:
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":  # pragma: no cover
            logger.debug(
                "Skipping QMainWindow geometry/state comparison in offscreen mode."
            )
            return False

        key = widget.property(SETTINGS_PROPERTY) or "MainWindow"
        settings.beginGroup(key)
        current_geometry = widget.saveGeometry()
        saved_geometry = settings.value("geometry", type=QByteArray)
        geometry_differs = current_geometry != saved_geometry
        current_state = widget.saveState()
        saved_state = settings.value("state", type=QByteArray)
        state_differs = current_state != saved_state
        settings.endGroup()
        if geometry_differs or state_differs:
            return True
        return False

    def get_signals_to_monitor(self, widget: QMainWindow) -> List[SignalInstance]:
        return []


@runtime_checkable
class SettingsManager(Protocol):
    """
    Defines the public interface for the settings manager to track
    the state of Qt widgets and custom data.

    Unlike widget state, custom data is synced automatically upon save.
    """

    touched_changed: SignalInstance
    """
    Signal emitted when the 'touched' state of the manager changes.

    Emits:
        bool: The new 'touched' state (True if touched, False if untouched).
    """

    @property
    def is_touched(self) -> bool:
        """
        Indicates whether the managed state has changed since the last save or load operation.
        This only includes changes to registered widgets.

        Returns:
            bool: True if the state is considered 'touched' (modified), False otherwise.
        """
        ...

    @property
    def custom_data_keys(self) -> List[str]:
        """
        Keys for the data stored in `CUSTOM_DATA_GROUP`.

        Returns:
            A list of strings with the current custom data keys.
        """
        ...

    def save(self) -> None:
        """
        Saves the current state of all managed widgets to the underlying QSettings.
        """
        ...

    def load(self) -> None:
        """
        Loads the state from the default underlying storage into the managed widgets.
        """
        ...

    def register_handler(
        self, widget_type: Any, handler_instance: SettingsHandler
    ) -> None:
        """
        Registers a specific handler instance for a given widget type.

        This allows customizing or adding support for saving, loading, comparing,
        and monitoring different QWidget subclasses. If a handler for this
        exact type already exists, it will be replaced.

        Args:
            widget_type: The class of the widget (e.g., QLineEdit, MyCustomWidget).
            handler_instance: An object conforming to the SettingsHandler protocol.

        Raises:
            TypeError: If `handler_instance` does not conform to SettingsHandler.
        """
        ...

    def save_custom_data(self, key: str, data: Any) -> None:
        """
        Saves arbitrary pickleable data associated with a specific key to the
        default underlying storage.

        This data is stored independently of widget states and is synced automatically.

        Args:
            key: A unique identifier for the data.
            data: The Python object to save. Must be pickleable.
        """
        ...

    def load_custom_data(self, key: str, expected_type: type[T]) -> T | None:
        """
        Loads previously saved (pickled) custom data associated with a specific key from
        the default underlying storage.

        Performs a type check against the `expected_type` after unpickling.
        Loading custom data does *not* change the 'touched' state of the manager.

        Args:
            key: The unique string identifier used when saving the data.
            expected_type: The expected type of the loaded data (e.g., dict, list, MyClass).

        Returns:
            The loaded data cast to `expected_type` if found and type-compatible,
            otherwise None.
        """
        ...

    def delete_custom_data(self, key: str) -> None:
        """
        Deletes previously saved custom data associated with a specific key.

        Args:
            key: The unique string identifier used when saving the data.
        """
        ...

    def skip_widget(self, widget: QWidget) -> None:
        """
        Explicitly prevents the manager from saving, loading, comparing, or
        monitoring signals for the specified widget instance.

        The widget will be ignored during all manager operations until `unskip_widget`
        is called for it. Any connected signals for this widget will be disconnected.

        Args:
            widget: The specific QWidget instance to skip.
        """
        ...

    def unskip_widget(self, widget: QWidget) -> None:
        """
        Resumes management for a previously skipped widget instance.

        If the widget has the necessary `SETTINGS_PROPERTY` and a suitable handler
        is available, its signals will be reconnected, and it will be included
        in future save, load, and compare operations.

        Args:
            widget: The specific QWidget instance to unskip.
        """
        ...

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the current state of managed widgets to a
        specified file path using an appropriate format (e.g., INI).

        Args:
            filepath: The path to the file where settings should be saved.
        """
        ...

    def load_from_file(self, filepath: str) -> None:
        """
        Loads widget states from a specified file path.

        Args:
            filepath: The path to the file from which settings should be loaded.
        """
        ...

    def mark_untouched(self) -> None:
        """
        Manually forces the manager's state to 'untouched'.
        """
        ...

    def mark_touched(self) -> None:
        """
        Manually forces the manager's state to 'touched'.
        """
        ...

    def has_unsaved_changes(self, source: Union[str, QSettings] | None = None) -> bool:
        """
        Compares the current state of managed widgets against a saved state.

        This method iterates through managed widgets and uses their respective
        handler's `compare` method. It does *not* consider changes in custom data
        saved via `save_custom_data`. It also does not modify the UI or the
        manager's `is_touched` state.

        Args:
            source: Specifies the state to compare against.
                - None: Compares against the default QSettings storage.
                - str: A file path to an settings file (e.g., ".ini").
                - QSettings: An existing QSettings object.

        Returns:
            True if any managed widget's current state differs from the state
            found in the specified source.

        Raises:
            TypeError: If source is not None, str, or QSettings.
        """
        ...

    def get_managed_widgets(self) -> List[QWidget]:
        """
        Retrieves a list of all QWidget instances currently being managed.

        This includes widgets that have the `SETTINGS_PROPERTY` set, have a
        registered handler, and are not currently skipped. The traversal starts
        from the main window.

        Returns:
            A list of managed QWidget instances.
        """
        ...


HandlerRegistry = Dict[type[Any], SettingsHandler]


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

    @property
    def custom_data_keys(self) -> List[str]:
        self._settings.beginGroup(CUSTOM_DATA_GROUP)
        keys = self._settings.childKeys()
        self._settings.endGroup()
        return keys

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

    def _perform_widget_save(self, settings: QSettings) -> None:
        main_window = self._find_main_window()
        if main_window:
            self._save_widget(main_window, settings)
        else:  # pragma: no cover
            logger.warning("Could not find main window to initiate save.")

    def _perform_widget_load(self, settings: QSettings) -> None:
        self._disconnect_all_widget_signals()
        main_window = self._find_main_window()
        if main_window:
            try:
                # Load state recursively. Signal blocking will happen inside _process_widget_and_recurse
                self._load_widget(main_window, settings)
            except Exception as e:  # pragma: no cover
                logger.error(f"Error during recursive load: {e}", exc_info=True)

            # Connect signals *after* all widgets have loaded their state
            self._connect_signals(main_window)
        else:  # pragma: no cover
            logger.warning("Could not find main window for load/signal connection.")

    def save(self) -> None:
        logger.info("Saving state to default settings.")
        self._perform_widget_save(self._settings)
        self._settings.sync()
        status = self._settings.status()
        if status != QSettings.Status.NoError:  # pragma: no cover
            logger.error(f"Error syncing settings during save: {status}")
        else:
            logger.info("Successfully saved settings")

        self.mark_untouched()

    def load(self) -> None:
        logger.info("Loading state from default settings.")
        self._perform_widget_load(self._settings)
        self.mark_untouched()

    def save_to_file(self, filepath: str) -> None:
        logger.info(f"Saving state to file: {filepath}")
        file_settings = QSettings(filepath, QSettings.Format.IniFormat)
        self._perform_widget_save(file_settings)

        self._copy_custom_data(
            source_settings=self._settings,
            dest_settings=file_settings,
            clear_dest_first=True,
        )

        file_settings.sync()
        status = file_settings.status()
        if status != QSettings.Status.NoError:  # pragma: no cover
            logger.error(
                f"Error syncing settings to file '{filepath}' during save: {status}"
            )
        else:
            logger.info(f"Successfully saved settings to {filepath}")
        del file_settings  # releases qt lock

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

        self._perform_widget_load(file_settings)

        self._copy_custom_data(
            source_settings=file_settings,
            dest_settings=self._settings,
            clear_dest_first=True,  # Always clear when loading from file
        )

        self._settings.sync()
        if self._settings.status() != QSettings.Status.NoError:  # pragma: no cover
            logger.error(
                f"Error syncing default settings after loading custom data from file: {self._settings.status()}"
            )

        self.mark_untouched()
        del file_settings  # releases qt lock

    def _copy_custom_data(
        self,
        source_settings: QSettings,
        dest_settings: QSettings,
        clear_dest_first: bool = False,
    ) -> None:
        source_id = source_settings.fileName() or "in-memory-source"
        dest_id = dest_settings.fileName() or "in-memory-dest"
        logger.debug(
            f"Starting custom data copy: {source_id} -> {dest_id} (Clear Dest: {clear_dest_first})"
        )

        # Prevent self-clearing when source and destination are the same file path
        are_same_file = os.path.normpath(source_id) == os.path.normpath(dest_id)

        if clear_dest_first and not are_same_file:
            dest_settings.beginGroup(CUSTOM_DATA_GROUP)
            dest_settings.remove("")
            dest_settings.endGroup()
            logger.debug(f"Cleared custom data group in destination {dest_id} before copy.")
        elif clear_dest_first and are_same_file:
            logger.debug(f"Skipping custom data clear: source and destination are the same QSettings object.")

        logger.debug(
            f"Reading custom data keys from source group '{CUSTOM_DATA_GROUP}' in {source_id}"
        )
        source_settings.beginGroup(CUSTOM_DATA_GROUP)
        custom_keys = source_settings.childKeys()
        source_settings.endGroup()

        if not custom_keys:
            logger.debug(
                f"No custom data keys found in source group '{CUSTOM_DATA_GROUP}' of {source_id}."
            )
            return

        logger.debug(
            f"Found {len(custom_keys)} custom data keys in source {source_id}. Copying to {dest_id}."
        )
        dest_settings.beginGroup(CUSTOM_DATA_GROUP)
        copied_count = 0
        skipped_count = 0
        for key in custom_keys:
            full_source_key = f"{CUSTOM_DATA_GROUP}/{key}"
            value = source_settings.value(full_source_key)
            if value is not None:
                dest_settings.setValue(key, value)
                copied_count += 1
            else:  # pragma: no cover
                logger.warning(
                    f"Could not read value for custom data key '{full_source_key}' during copy."
                )
                skipped_count += 1
        dest_settings.endGroup()
        logger.debug(
            f"Finished custom data copy ({copied_count} copied, {skipped_count} skipped): {source_id} -> {dest_id}"
        )

    def register_handler(
        self, widget_type: type[QWidget], handler_instance: SettingsHandler
    ) -> None:
        if not isinstance(handler_instance, SettingsHandler):
            raise TypeError("Handler must conform to SettingsHandler protocol.")
        logger.debug(f"Registering handler for type {widget_type.__name__}")
        self._handlers[widget_type] = handler_instance

    def _save_custom_data_impl(self, settings: QSettings, key: str, data: Any) -> None:
        try:
            pickled_data = pickle.dumps(data)
            settings_key = (
                f"{CUSTOM_DATA_GROUP}/{key.value if isinstance(key, Enum) else key}"
            )
            settings.setValue(settings_key, QByteArray(pickled_data))
        except (pickle.PicklingError, TypeError, AttributeError) as e:
            logger.error(
                f"Could not pickle custom data for key '{key}': {e}", exc_info=True
            )

    def _load_custom_data_impl(self, settings: QSettings, key: str) -> Optional[Any]:
        settings_key = (
            f"{CUSTOM_DATA_GROUP}/{key.value if isinstance(key, Enum) else key}"
        )
        value = settings.value(settings_key)
        if value is not None:
            # Attempt to convert to bytes if not already bytes
            try:
                data_bytes = value if isinstance(value, bytes) else bytes(value)
            except TypeError:  # pragma: no cover # bytes(value) fails
                data_bytes = None  # Treat as invalid data

            if isinstance(data_bytes, bytes) and data_bytes:
                try:
                    return pickle.loads(data_bytes)
                except pickle.UnpicklingError as e:
                    logger.warning(f"Could not unpickle data for key '{key}': {e}")
                except Exception as e:  # pragma: no cover
                    logger.error(
                        f"Error unpickling data for key '{key}': {e}", exc_info=True
                    )
            else:  # pragma: no cover # Difficult to reliably test this path due to type coercion/bytes() behavior
                logger.warning(
                    f"No valid data found for custom data key '{key}' (type: {type(value)})"
                )
        return None

    def delete_custom_data(self, key: str) -> None:
        settings_key = (
            f"{CUSTOM_DATA_GROUP}/{key.value if isinstance(key, Enum) else key}"
        )
        if self._settings.contains(settings_key):
            self._settings.remove(settings_key)
            logger.debug(f"Deleted custom data for key '{key}'.")
        else:
            logger.warning(f"No custom data found for key '{key}' to delete.")

    def save_custom_data(self, key: str, data: Any) -> None:
        self._save_custom_data_impl(self._settings, key, data)
        self._settings.sync()

    def load_custom_data(self, key: str, expected_type: type[T]) -> Optional[T]:
        unpickled_data = self._load_custom_data_impl(self._settings, key)

        if unpickled_data is None:
            logger.debug(f"No custom data found for key '{key}'.")
            return None

        if isinstance(unpickled_data, expected_type):
            logger.debug(
                f"Successfully loaded custom data for key '{key}' with expected type {expected_type.__name__}."
            )
            return cast(T, unpickled_data)
        else:
            logger.warning(
                f"Loaded custom data for key '{key}' has type {type(unpickled_data).__name__}, "
                f"which does not match the expected type {expected_type.__name__}. Returning None."
            )
            return None

    def _find_main_window(self) -> QMainWindow | None:
        for widget in QApplication.topLevelWidgets():
            if (
                isinstance(widget, QMainWindow)
                and widget.property(SETTINGS_PROPERTY) is not None
            ):
                return cast(QMainWindow, widget)
        # pragma: no cover # off-screen
        logger.warning(
            "No QMainWindow with SETTINGS_PROPERTY found among top-level widgets."
        )
        return None

    def _get_handler(self, widget: QWidget) -> SettingsHandler | None:
        widget_class = type(widget)
        if widget_class in self._handlers:
            return self._handlers[widget_class]
        for base_class in widget_class.__mro__[1:]:
            if base_class in self._handlers:
                return self._handlers[base_class]
        return None

    def skip_widget(self, widget: QWidget) -> None:
        if widget not in self._skipped_widgets:  # pragma: no cover
            logger.debug(
                f"Skipping widget: {widget.property(SETTINGS_PROPERTY)} ({type(widget).__name__})"
            )
            self._skipped_widgets.add(widget)
            self._disconnect_widget_signals(widget)

    def unskip_widget(self, widget: QWidget) -> None:
        if widget in self._skipped_widgets:  # pragma: no cover
            logger.debug(
                f"Unskipping widget: {widget.property(SETTINGS_PROPERTY)} ({type(widget).__name__})"
            )
            self._skipped_widgets.remove(widget)
            if not self._should_skip_widget(widget):
                handler = self._get_handler(widget)
                if handler:  # pragma: no cover
                    self._connect_widget_signals(widget, handler)  # pragma: no cover

    def _should_skip_widget(self, widget: QWidget) -> bool:
        if widget in self._skipped_widgets:  # pragma: no cover
            return True
        key = widget.property(SETTINGS_PROPERTY)
        if key is None or not isinstance(key, str) or not key:  # pragma: no cover
            return True
        return False

    def _process_widget_and_recurse(
        self,
        parent: QWidget,
        settings: QSettings | None,
        operation: str,
        managed_list: List[QWidget] | None = None,
    ) -> bool:
        # --- 1. Check for explicit skipping FIRST (prevents any processing or recursion) ---
        if parent in self._skipped_widgets:  # pragma: no cover
            logger.debug(
                f"Widget {self._get_settings_key(parent) or type(parent).__name__} is explicitly skipped."
            )
            return False

        # --- 2. Process the parent widget itself (if it's meant to be managed) ---
        parent_difference_found = False
        handler_to_use = self._get_handler(parent)

        # Only process parent if it's NOT skipped for processing (has key) AND has a handler
        if not self._should_skip_widget_processing(parent) and handler_to_use:
            settings_key = self._get_settings_key(parent)  # We know key exists here
            handler_to_use = cast(
                SettingsHandler, handler_to_use
            )  # We know handler exists
            settings_key = cast(str, settings_key)  # We know key is a non-empty string

            try:
                if operation == "save" and settings:
                    logger.debug(
                        f"Saving state for '{settings_key}' ({type(parent).__name__}) using {type(handler_to_use).__name__}"
                    )
                    handler_to_use.save(parent, settings)
                elif operation == "load" and settings:
                    logger.debug(
                        f"Loading state for '{settings_key}' ({type(parent).__name__}) using {type(handler_to_use).__name__}"
                    )
                    blocker = QSignalBlocker(parent)
                    try:
                        handler_to_use.load(parent, settings)
                        parent.updateGeometry()
                        parent.update()
                    finally:
                        blocker.unblock()
                elif operation == "connect":
                    logger.debug(
                        f"Connecting signals for '{settings_key}' ({type(parent).__name__}) using {type(handler_to_use).__name__}"
                    )
                    self._connect_widget_signals(parent, handler_to_use)
                elif operation == "compare" and settings:
                    logger.debug(
                        f"Comparing state for '{settings_key}' ({type(parent).__name__}) using {type(handler_to_use).__name__}"
                    )
                    if handler_to_use.compare(parent, settings):
                        logger.info(
                            f"Difference detected in widget: '{settings_key}' ({type(parent).__name__}) by its handler."
                        )
                        parent_difference_found = True
                elif operation == "collect" and managed_list is not None:
                    logger.debug(
                        f"Collecting managed widget: '{settings_key}' ({type(parent).__name__})"
                    )
                    managed_list.append(parent)
            except Exception as e:
                logger.error(
                    f"Error during '{operation}' on widget '{settings_key}' ({type(parent).__name__}): {e}",
                    exc_info=True,
                )
                if operation == "compare":
                    logger.warning(
                        f"Treating widget '{settings_key}' as different due to error during comparison."
                    )
                    parent_difference_found = True

            if parent_difference_found:
                return True  # Difference found in parent during compare, stop recursion

        # --- 3. Determine children and Recurse (Almost always recurse for QWidgets) ---
        # We need to look inside containers even if the container itself isn't managed (e.g., nameless QWidget tab content)
        # The only time we might NOT recurse is if the parent *was* processed AND its handler is known
        # to handle all its children implicitly (rare, maybe a custom complex widget handler).
        # For standard Qt widgets, assume recursion is needed.

        # Let's simplify: always try to find children for QWidgets
        children_to_process: list[QWidget] = []
        parent_identifier = (
            self._get_settings_key(parent) or f"Unnamed {type(parent).__name__}"
        )

        if isinstance(parent, QMainWindow):
            logger.debug(f"Getting children for QMainWindow: {parent_identifier}")
            cw = parent.centralWidget()
            if cw:
                children_to_process.append(cw)
            # Add toolbars/docks if needed
        elif isinstance(parent, QTabWidget):
            logger.debug(f"Getting children for QTabWidget: {parent_identifier}")
            for i in range(parent.count()):
                tab_child = parent.widget(i)
                if tab_child:
                    children_to_process.append(tab_child)
        # elif isinstance(parent, QScrollArea): # Example for other specific containers
        #    content = parent.widget()
        #    if content: children_to_process.append(content)
        else:
            # General case: Find direct QWidget children for QGroupBox, QWidget containers, etc.
            logger.debug(f"Getting direct children for: {parent_identifier}")
            children_to_process = parent.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
            )  # type: ignore

        # --- 4. Recurse into found children ---
        logger.debug(
            f"Found {len(children_to_process)} children for {parent_identifier}. Processing them."
        )
        for child in children_to_process:
            if self._process_widget_and_recurse(
                child, settings, operation, managed_list
            ):
                if operation == "compare":
                    logger.debug(
                        f"Difference found in child {self._get_settings_key(child) or type(child).__name__} of {parent_identifier}, propagating."
                    )
                    return True  # Difference found in a child, propagate up

        # No difference found in parent (if compared) or any children
        return False

    def _get_settings_key(self, widget: QWidget) -> str | None:
        """Safely retrieves the settings key from the widget's property."""
        key = widget.property(SETTINGS_PROPERTY)
        if key is not None and isinstance(key, str) and key:
            return key
        return None

    def _should_skip_widget_processing(self, widget: QWidget) -> bool:
        if widget in self._skipped_widgets:  # pragma: no cover
            logger.debug(
                f"Widget {self._get_settings_key(widget) or type(widget).__name__} is explicitly skipped."
            )
            return True
        key = self._get_settings_key(widget)
        if key is None:
            logger.debug(
                f"Widget {type(widget).__name__} lacks a valid '{SETTINGS_PROPERTY}' property - skipping direct processing."
            )
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

    def _connect_widget_signals(
        self, widget: QWidget, handler: SettingsHandler
    ) -> None:
        if widget in self._connected_signals:
            return
        if self._should_skip_widget(widget):  # pragma: no cover
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
                            # Covered by test_connect_invalid_signal_object
                            logger.warning(
                                f"Invalid signal object for {widget.property(SETTINGS_PROPERTY)}: {signal}"
                            )
                    except Exception as e:
                        # Covered by test_connect_signal_connect_error
                        logger.warning(
                            f"Failed to connect signal {getattr(signal, 'signal', signal)} for {widget.property(SETTINGS_PROPERTY)}: {e}"
                        )
                if connected_list:
                    self._connected_signals[widget] = connected_list
        except Exception as e:  # pragma: no cover # Handler get_signals error covered by test_exception_getting_signals
            logger.error(
                f"Error getting signals for widget {widget.property(SETTINGS_PROPERTY)} ({type(widget).__name__}): {e}",
                exc_info=True,
            )

    def _disconnect_widget_signals(self, widget: QWidget) -> None:
        if widget in self._connected_signals:
            for signal in self._connected_signals[widget]:
                try:
                    signal.disconnect(self._on_widget_changed)
                except (
                    TypeError,
                    RuntimeError,
                ):  # pragma: no cover # Qt disconnect errors hard to force reliably
                    pass  # Covered by test_disconnect_error_handling (attempted)
            del self._connected_signals[widget]

    def _disconnect_all_widget_signals(self) -> None:
        logger.debug("Disconnecting all widget signals.")
        widgets_to_disconnect = list(self._connected_signals.keys())
        for widget in widgets_to_disconnect:
            self._disconnect_widget_signals(widget)
        self._connected_signals.clear()

    def has_unsaved_changes(self, source: Union[str, QSettings] | None = None) -> bool:
        settings: QSettings | None = None
        temp_settings = False
        if source is None:
            settings = self._settings
            logger.debug("Comparing against default settings.")
        elif isinstance(source, str):
            logger.debug(f"Comparing against settings file: {source}")
            settings = QSettings(source, QSettings.Format.IniFormat)
            temp_settings = True
            if settings.status() != QSettings.Status.NoError:
                # Covered by test_has_unsaved_changes_invalid_file_source
                logger.warning(
                    f"Cannot compare: Failed to load settings from {source}. Status: {settings.status()}"
                )
                return False  # Covered by test_has_unsaved_changes_invalid_file_source
        elif isinstance(source, QSettings):
            settings = source
            logger.debug("Comparing against provided QSettings object.")
        else:
            raise TypeError(
                "Source must be None, a filepath string, or a QSettings object."
            )

        main_window = self._find_main_window()
        if not main_window:  # pragma: no cover # Hard to reliably test without mocking QApplication itself
            logger.warning("Cannot compare: Main window not found.")
            return False  # pragma: no cover

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
