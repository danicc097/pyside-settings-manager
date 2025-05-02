# pyside-settings-manager

[![Code Coverage](https://codecov.io/gh/danicc097/pyside-settings-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/danicc097/pyside-settings-manager)
[![GitHub Actions CI Status](https://github.com/danicc097/pyside-settings-manager/actions/workflows/tests.yaml/badge.svg)](https://github.com/danicc097/pyside-settings-manager/actions/workflows/tests.yaml)

Recursively save and restore states of PySide6 widgets using a handler-based system, providing a 'touched' state indicator and the ability to check for unsaved changes.

## Features

*   **Recursive Traversal:** Automatically finds and manages state for supported
    widgets within a `QMainWindow` or other container widgets like `QTabWidget`.
*   **Handler-Based:** Provides a flexible system where the logic for saving, loading, comparing, and monitoring specific widget types is encapsulated in dedicated handler classes. Default handlers are provided for common PySide6 widgets.
*   **Extensible:** Easily register custom handlers for your own widget types or to override default behavior.
*   **Touched State:** Tracks whether any managed widget or custom data has been changed since the last `save_state` or `load_state` call.
*   **Unsaved Changes Check:** Provides a method to explicitly check if the current state of the managed widgets differs from a saved state (in the default settings or a specific file).
*   **Custom Data:** Save and load arbitrary pickleable Python objects alongside widget states.
*   **Skipping:** Explicitly exclude specific widgets from management.
*   **File-Based Settings:** Save and load states to/from `.ini` files using `QSettings`.

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
*   `QTabWidget`
*   `QSlider`

## Installation

Currently via github, e.g.:

```bash
uv add "git+https://github.com/danicc097/pyside-settings-manager.git@vX.Y.Z"
```

## Usage

1.  **Set the `SETTINGS_PROPERTY` property:** Add the property entry to widgets that you want to be managed. The property should be a
    unique string identifier for that widget's state in the settings file.
    Widgets without this property will be ignored by default.
2.  **Create a `QSettings` instance:** Decide where you want your settings to be stored (e.g., application-specific user settings, a project file).
3.  **Create the `SettingsManager`:** Instantiate the manager with your `QSettings` object.
4.  **Load State:** Call `load_state()` usually after your UI is fully set up. This will restore the saved states of your managed widgets.
5.  **Save State:** Call `save_state()` when you want to persist the current
    state of your managed widgets (e.g., on application close, shortcuts).
6.  **Monitor Touched State:** Connect to the `touched_changed` signal or check
    the `is_touched` property to update UI elements (like enabling a "Save"
    button or updating the window title).
7.  **Check for Unsaved Changes:** Use `has_unsaved_changes()` to determine if the current UI state differs from the last saved state, especially before closing or performing actions that would discard unsaved changes.

```python
import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QWidget,
    QPushButton,
)
from PySide6.QtCore import QSettings

from pyside_settings_manager import create_settings_manager, SETTINGS_PROPERTY


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setProperty(SETTINGS_PROPERTY, "mainWindow")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.my_checkbox = QCheckBox("Enable Feature")
        self.my_checkbox.setProperty(SETTINGS_PROPERTY, "featureCheckbox")
        layout.addWidget(self.my_checkbox)

        self.another_checkbox = QCheckBox("Another Feature (untracked)")

        layout.addWidget(self.another_checkbox)

        self.save_button = QPushButton("Save Settings")
        layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Settings")
        layout.addWidget(self.load_button)

        self.status_label = QPushButton("Status: Untouched")
        self.status_label.setEnabled(False)
        layout.addWidget(self.status_label)

        self.check_changes_button = QPushButton("Check for Unsaved Changes")
        layout.addWidget(self.check_changes_button)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # temporary settings for this example
    settings_file = "my_app_settings.ini"
    settings = QSettings(settings_file, QSettings.Format.IniFormat)

    window = MyWindow()
    manager = create_settings_manager(settings)

    window.save_button.clicked.connect(manager.save_state)
    window.load_button.clicked.connect(manager.load_state)

    def update_status_label(touched: bool):
        window.status_label.setText(f"Status: {'Touched' if touched else 'Untouched'}")
        window.save_button.setEnabled(touched)

    manager.touched_changed.connect(update_status_label)

    # Would usually be used in closeEvent to prompt the user to discard, save, or cancel
    def check_unsaved():
        has_changes = manager.has_unsaved_changes()
        print(f"Has unsaved changes? {has_changes}")

    window.check_changes_button.clicked.connect(check_unsaved)

    manager.load_state()
    update_status_label(manager.is_touched)

    window.show()

    sys.exit(app.exec())

    # Demo cleanup
    if os.path.exists(settings_file):
        os.remove(settings_file)

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
# Now, any QLineEdit with the ``SETTINGS_PROPERTY`` property will use your custom handler instead of the default handler
```

## Custom Data

You can save and load arbitrary pickleable data using `save_custom_data` and `load_custom_data`:

```python
manager.save_custom_data("user_preferences", {"theme": "dark", "font_size": 12})

prefs = manager.load_custom_data("user_preferences")
if prefs:
    print(f"Loaded preferences: {prefs}")

# Saving custom data marks the manager as touched
assert manager.is_touched

# Loading custom data does NOT mark the manager as touched
manager.mark_untouched()
loaded_prefs = manager.load_custom_data("user_preferences")
assert not manager.is_touched
```

## Skipping Widgets

To prevent a specific widget from being saved, loaded, compared, or monitored for the `touched` state, use `skip_widget()`:

```python
# Assume it exists and has the settings property
manager.skip_widget(window.my_checkbox)

# Changes to window.my_checkbox will not mark the state as touched,
# and its state won't be saved or loaded.

# To re-enable management:
manager.unskip_widget(window.my_checkbox)
```

## Checking for Unsaved Changes

The `has_unsaved_changes()` method allows you to check if the current UI state, for all *managed* widgets, differs from a saved state.

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

This method traverses the managed widgets and calls their respective handlers' `compare` methods. It returns `True` as soon as the first difference is detected. It does *not* modify the UI or the manager's `is_touched` state. Changes in custom data are *not* considered by `has_unsaved_changes`.

## Development

See `tests` directory for detailed examples covering various widgets and handler behaviors.

To run tests:

```bash
uv run pytest
```

## Contribution

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
