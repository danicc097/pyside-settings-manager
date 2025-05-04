# pyside-settings-manager

[![Code Coverage](https://codecov.io/gh/danicc097/pyside-settings-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/danicc097/pyside-settings-manager)
[![GitHub Actions CI Status](https://github.com/danicc097/pyside-settings-manager/actions/workflows/tests.yaml/badge.svg)](https://github.com/danicc097/pyside-settings-manager/actions/workflows/tests.yaml)
[![PyPI](https://img.shields.io/pypi/v/pyside-settings-manager.svg?logo=python&logoColor=white)](https://pypi.org/project/pyside-settings-manager/)

Recursively save and restore states of PySide6 widgets using a handler-based system, providing a 'touched' state indicator and the ability to check for unsaved changes.

## Features

*   **Recursive Traversal:** Automatically finds and manages state for supported
    widgets within a `QMainWindow` or other container widgets like `QTabWidget` and `QGroupBox`.
*   **Handler-Based:** Provides a flexible system where the logic for saving, loading, comparing, and monitoring specific widget types is encapsulated in dedicated handler classes. Default handlers are provided for common PySide6 widgets.
*   **Extensible:** Easily register custom handlers for your own widget types or to override default behavior.
*   **Touched State:** Tracks whether any managed widget or custom data has been changed since the last `save` or `load` call.
*   **Unsaved Changes Check:** Provides a method to explicitly check if the current state of the managed widgets differs from a saved state (in the default settings or a specific file).
*   **Custom Data:** Save and load arbitrary pickleable Python objects alongside widget states.
*   **Skipping:** Explicitly exclude specific widgets from management.
*   **File-Based Settings:** Save and load states to/from `.ini` files using `QSettings`, including options to save/load to specific files.

## Supported Widgets (with default handlers)

*   `QMainWindow` (geometry and state)
*   `QCheckBox`
*   `QLineEdit`
*   `QPushButton` (if checkable)
*   `QComboBox` (index and text if editable)
*   `QSpinBox`
*   `QDoubleSpinBox`
*   `QRadioButton`
*   `QTextEdit`
*   `QTabWidget` (current index if managed)
*   `QSlider`

*(Note: Container widgets like `QWidget`, `QGroupBox` and `QTabWidget` are traversed to find managed children, but don't have their own state saved by default unless a specific handler is registered for them).*

## Installation

Via PyPI:

```bash
pip install pyside-settings-manager
```

Via GitHub, e.g. using `uv`:

```bash
uv add "git+https://github.com/danicc097/pyside-settings-manager.git@vX.Y.Z"
```

## Usage

1.  **Set the `SETTINGS_PROPERTY` property:** Add the property entry to widgets that you want to be managed. The property value should be a unique string identifier for that widget's state within the settings file scope. Widgets without this property will be ignored by default.
2.  **Create a `QSettings` instance:** Decide where you want your settings to be stored (e.g., application-specific user settings, a project file).

3.  **Create the `SettingsManager`:** Instantiate the manager with your `QSettings` object.
4.  **Load State:** Call `manager.load()` usually after your UI is fully set up. This will restore the saved states of your managed widgets from the default `QSettings`.
5.  **Save State:** Call `manager.save()` when you want to persist the current state of your managed widgets to the default `QSettings` (e.g., on application close, via a save button/shortcut).
6.  **Monitor Touched State:** Connect to the `touched_changed` signal or check the `is_touched` property to update UI elements (like enabling a "Save" button or adding an asterisk to the window title).
    ```python
    def on_touched_changed(touched):
        save_button.setEnabled(touched)
        window.setWindowTitle(f"My App {'*' if touched else ''}")

    manager.touched_changed.connect(on_touched_changed)
    ```
7.  **Check for Unsaved Changes:** Use `manager.has_unsaved_changes()` to determine if the current UI state differs from the last saved state, especially before closing or performing actions that would discard unsaved changes.

Check out the ``examples`` folder for self-contained demo apps:

```bash
uv run .\examples\basic.py
```

## Custom Handlers

You can register custom handlers for specific widget types or your own custom widgets by creating a class that implements the `pyside_settings_manager.settings::SettingsHandler` protocol:

```python
from typing import List, Any
from PySide6.QtCore import QSettings, SignalInstance, QWidget
from PySide6.QtWidgets import QLineEdit
from pyside_settings_manager.settings import SettingsHandler, SETTINGS_PROPERTY

class CustomUppercaseLineEditHandler(SettingsHandler):
    def save(self, widget: QLineEdit, settings: QSettings) -> None:
        settings.setValue(widget.property(SETTINGS_PROPERTY), widget.text().upper())

    def load(self, widget: QLineEdit, settings: QSettings) -> None:
        value = settings.value(widget.property(SETTINGS_PROPERTY), type=str)
        if value is not None:
            widget.setText(str(value))

    def compare(self, widget: QLineEdit, settings: QSettings) -> bool:
         """Returns True if current state != saved state"""
         key = widget.property(SETTINGS_PROPERTY)
         current_value: str = widget.text()
         # Load the value saved by this handler's save method (uppercase)
         saved_value = settings.value(key, type=str)
         if saved_value is None:
             return bool(current_value)

         return current_value.upper() != str(saved_value)


    def get_signals_to_monitor(self, widget: QLineEdit) -> List[SignalInstance]:
        # Return a list of signals that indicate a change requiring the 'touched' state
        return [widget.textChanged]

manager.register_handler(QLineEdit, CustomUppercaseLineEditHandler())
# Now, any QLineEdit with the ``SETTINGS_PROPERTY`` property will use your custom handler
# instead of the default one.
```

## Custom Data

You can save and load arbitrary pickleable data using `save_custom_data` and `load_custom_data`:

```python
manager.save_custom_data("user_preferences", {"theme": "dark", "font_size": 12})

prefs = manager.load_custom_data("user_preferences", dict) # {"theme": "dark", "font_size": 12}
```

Custom data is stored under a specific group based on ``CUSTOM_DATA_GROUP`` (e.g., `[customData]`). When using `save_to_file` and `load_from_file`, this custom data is also transferred. Note that `load_from_file` will overwrite any existing custom data in the manager's default `QSettings` with the custom data from the loaded file.

## Skipping Widgets

To prevent a specific widget instance from being saved, loaded, compared, or monitored for the `touched` state, use `skip_widget()`:

```python
manager.skip_widget(window.my_checkbox)

# Changes to window.my_checkbox will NOT mark the state as touched,
# and its state won't be saved, loaded, or compared.

# To re-enable management:
manager.unskip_widget(window.my_checkbox)
```

## Checking for Unsaved Changes

The `has_unsaved_changes()` method allows you to check if the current UI state for all *managed* (not skipped, has property, has handler) widgets differs from a saved state.

```python
# Check against the default settings file used by the manager
manager.has_unsaved_changes()
# Check against a specific settings file
manager.has_unsaved_changes(source="backup_settings.ini")
# Check against a specific QSettings object
alt_settings = QSettings("temp.ini", QSettings.Format.IniFormat)
# ...
manager.has_unsaved_changes(source=alt_settings)
```

This method traverses the managed widgets and calls their respective handlers'
`compare` methods. It returns `True` as soon as the first difference is
detected. It does *not* modify the UI or the manager's `is_touched` state.
Changes in custom data saved via `save_custom_data` are *not* considered by
`has_unsaved_changes`; these are immediately synced.

## Development

See the `src/tests` directory for detailed examples covering various widgets and handler behaviors.

To run tests using `uv`:

```bash
uv run pytest
```

## Contribution

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the Apache 2.0 License - see the
[LICENSE](LICENSE) file for details.

However, it relies on **PySide6**, which is licensed under the **LGPL v3**.
While the code specific to `pyside-settings-manager` is provided under the
Apache 2.0 license, any usage of this library inherently involves PySide6.
Users must ensure they comply with the terms of the LGPL v3 license regarding
their use and distribution.
