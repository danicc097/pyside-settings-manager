import signal
import sys
import os
import logging
from typing import Any, final, cast, Optional
from typing_extensions import override

from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QHBoxLayout,
)
from PySide6.QtCore import (
    QSettings,
    QObject,
    Signal,
    Slot,
    QFileSystemWatcher,
    QDir,
    QStandardPaths,
)
from PySide6.QtGui import QCloseEvent, QFontDatabase, QShowEvent, QTextCursor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from pyside_settings_manager import (
        create_settings_manager,
        SETTINGS_PROPERTY,
        SettingsManager,
    )
except ImportError:
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    )
    from pyside_settings_manager import (
        create_settings_manager,
        SETTINGS_PROPERTY,
        SettingsManager,
    )


@final
class QLogSignalEmitter(QObject):
    messageWritten = Signal(str, int)


@final
class QLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emitter = QLogSignalEmitter()

    @override
    def emit(self, record):
        try:
            msg = self.format(record)
            self.emitter.messageWritten.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


@final
class LogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Logs")
        self.setMinimumSize(800, 600)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_display.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )

        self._all_log_records: list[dict[str, Any]] = []

        self.log_level_filter_combo = QComboBox()
        self.log_level_filter_combo.addItem("ALL", logging.NOTSET)
        self.log_level_filter_combo.addItem("DEBUG", logging.DEBUG)
        self.log_level_filter_combo.addItem("INFO", logging.INFO)
        self.log_level_filter_combo.addItem("WARNING", logging.WARNING)
        self.log_level_filter_combo.addItem("ERROR", logging.ERROR)
        self.log_level_filter_combo.addItem("CRITICAL", logging.CRITICAL)
        self.log_level_filter_combo.currentIndexChanged.connect(
            self._apply_log_level_filter
        )

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.clear_button = self.button_box.addButton(
            "Clear", QDialogButtonBox.ButtonRole.ActionRole
        )

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Log Level:"))
        controls_layout.addWidget(self.log_level_filter_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.button_box)

        layout = QVBoxLayout()
        layout.addLayout(controls_layout)
        layout.addWidget(self.log_display)

        self.setLayout(layout)

        self.button_box.rejected.connect(self.reject)
        self.clear_button.clicked.connect(self._clear_logs)

    @Slot(str, int)
    def append_log(self, message: str, level: int):
        message = message.rstrip()
        if message:
            self._all_log_records.append({"message": message, "level": level})

            current_filter_level = self.log_level_filter_combo.currentData()
            if level >= current_filter_level:
                self.log_display.append(message)

                scrollbar = self.log_display.verticalScrollBar()
                if scrollbar.maximum() - scrollbar.value() < 50:
                    cursor = self.log_display.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.log_display.setTextCursor(cursor)

    def _apply_log_level_filter(self):
        current_filter_level = self.log_level_filter_combo.currentData()
        self.log_display.clear()

        for record in self._all_log_records:
            if record["level"] >= current_filter_level:
                self.log_display.append(record["message"])

        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()

    def _clear_logs(self):
        self._all_log_records.clear()
        self.log_display.clear()

    @override
    def showEvent(self, event: QShowEvent):
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()
        super().showEvent(event)

    @override
    def closeEvent(self, event: QCloseEvent):
        self.hide()
        event.ignore()


class MyWindow(QMainWindow):
    def __init__(self, manager: SettingsManager, settings_file_path: str):
        super().__init__()
        self.manager = manager
        self.settings_file_path = settings_file_path
        self.setProperty(SETTINGS_PROPERTY, "mainWindow")
        self.setWindowTitle("Settings Manager Example")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.my_checkbox = QCheckBox("Enable Feature (Tracked)")
        self.my_checkbox.setProperty(SETTINGS_PROPERTY, "featureCheckbox")
        layout.addWidget(self.my_checkbox)

        self.another_checkbox = QCheckBox("Another Feature (Untracked)")
        layout.addWidget(self.another_checkbox)

        custom_data_layout = QHBoxLayout()
        self.custom_key_input = QLineEdit("my_custom_setting")
        self.custom_key_input.setPlaceholderText("Custom Data Key")
        self.custom_value_input = QLineEdit("default value")
        self.custom_value_input.setPlaceholderText("Custom Data Value (string)")
        self.save_custom_button = QPushButton("Save Custom")
        self.load_custom_button = QPushButton("Load Custom")

        custom_data_layout.addWidget(QLabel("Key:"))
        custom_data_layout.addWidget(self.custom_key_input)
        custom_data_layout.addWidget(QLabel("Value:"))
        custom_data_layout.addWidget(self.custom_value_input)
        custom_data_layout.addWidget(self.save_custom_button)
        custom_data_layout.addWidget(self.load_custom_button)
        layout.addLayout(custom_data_layout)

        self.custom_data_display = QLabel("Loaded Custom Data: <None>")
        layout.addWidget(self.custom_data_display)

        controls_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Settings")
        self.load_button = QPushButton("Load Settings")
        self.check_changes_button = QPushButton("Check Unsaved")
        self.show_log_button = QPushButton("Show Logs")

        controls_layout.addWidget(self.save_button)
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.check_changes_button)
        controls_layout.addWidget(self.show_log_button)
        layout.addLayout(controls_layout)

        self.status_label = QLabel("Status: Untouched")
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel("Settings File Content:"))
        self.settings_file_display = QTextEdit()
        self.settings_file_display.setReadOnly(True)
        self.settings_file_display.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        layout.addWidget(self.settings_file_display)

        self.log_window = LogWindow(self)

        self.file_watcher = QFileSystemWatcher()
        if os.path.exists(self.settings_file_path):
            self.file_watcher.addPath(self.settings_file_path)
        elif os.path.exists(os.path.dirname(self.settings_file_path)):
            self.file_watcher.addPath(os.path.dirname(self.settings_file_path))

        self.file_watcher.fileChanged.connect(
            self._update_settings_file_display_from_signal
        )

        self.save_button.clicked.connect(self._save_settings_and_refresh)
        self.load_button.clicked.connect(self.manager.load)
        self.check_changes_button.clicked.connect(self._check_unsaved)
        self.show_log_button.clicked.connect(self._show_logs)
        self.save_custom_button.clicked.connect(self._save_custom)
        self.load_custom_button.clicked.connect(self._load_custom)

        self.manager.touched_changed.connect(self._update_status_label)

        self._update_settings_file_display()

    def _setup_file_watcher(self):
        if os.path.exists(self.settings_file_path):
            if self.settings_file_path not in self.file_watcher.files():
                self.file_watcher.addPath(self.settings_file_path)

    def _update_status_label(self, touched: bool):
        self.status_label.setText(f"Status: {'*TOUCHED*' if touched else 'Untouched'}")

    @Slot()
    def _save_settings_and_refresh(self):
        logging.info("Saving settings...")
        self.manager.save()  # FIXME: will fail with Status.AccessError but it's synced
        QtCore.QTimer.singleShot(250, self._update_settings_file_display)

    @Slot(str)
    def _update_settings_file_display_from_signal(self, path: str):
        if path == self.settings_file_path or os.path.dirname(path) == os.path.dirname(
            self.settings_file_path
        ):
            self._update_settings_file_display()

    def _check_unsaved(self):
        has_changes = self.manager.has_unsaved_changes()
        logging.info(f"Has unsaved changes? {has_changes}")

    def _show_logs(self):
        self.log_window.show()
        self.log_window.activateWindow()
        self.log_window.raise_()

    def _save_custom(self):
        key = self.custom_key_input.text().strip()
        value = self.custom_value_input.text()
        if key:
            self.manager.save_custom_data(key, value)
        else:
            logging.warning("Cannot save custom data: Key is empty.")

    def _load_custom(self):
        key = self.custom_key_input.text().strip()
        if key:
            try:
                loaded_value = self.manager.load_custom_data(key, str)
                if loaded_value is not None:
                    self.custom_data_display.setText(
                        f"Loaded Custom Data ('{key}'): {loaded_value}"
                    )
                    self.custom_value_input.setText(loaded_value)
                else:
                    self.custom_data_display.setText(
                        f"Loaded Custom Data ('{key}'): <Not Found>"
                    )

            except Exception as e:
                logging.error(
                    f"Error loading custom data for key '{key}': {e}", exc_info=True
                )
                self.custom_data_display.setText(
                    f"Loaded Custom Data ('{key}'): <Load Error>"
                )
        else:
            logging.warning("Cannot load custom data: Key is empty.")

    @Slot()
    def _update_settings_file_display(self):
        try:
            settings_dir = os.path.dirname(self.settings_file_path)
            if settings_dir and settings_dir not in self.file_watcher.directories():
                if os.path.exists(settings_dir):
                    self.file_watcher.addPath(settings_dir)

            if os.path.exists(self.settings_file_path):
                content = ""
                try:
                    with open(self.settings_file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as read_err:
                    logging.error(
                        f"Error reading file content: {read_err}", exc_info=True
                    )
                    content = f"<Error reading file: {read_err}>"

                self.settings_file_display.setPlainText(content)

                if self.settings_file_path not in self.file_watcher.files():
                    QtCore.QTimer.singleShot(
                        10, lambda: self.file_watcher.addPath(self.settings_file_path)
                    )

            else:
                self.settings_file_display.setPlainText(
                    f"Settings file '{os.path.basename(self.settings_file_path)}' does not exist yet"
                )

        except Exception as e:
            self.settings_file_display.setPlainText(f"Error updating display: {e}")


def setup_logging(log_window: LogWindow) -> QLogHandler:
    log_handler = QLogHandler()

    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - %(levelname)-7s - [%(name)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S",
    )
    log_handler.setFormatter(log_formatter)

    log_handler.emitter.messageWritten.connect(log_window.append_log)

    root_logger = logging.getLogger()
    if not any(isinstance(h, QLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(log_handler)

    root_logger.setLevel(logging.INFO)

    logging.getLogger("PySide6.QtOpenGL").setLevel(logging.WARNING)
    logging.getLogger("PySide6.QtGui").setLevel(logging.INFO)

    logging.info("Logging system configured.")
    return log_handler


def main():
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

    app = QApplication(sys.argv)

    settings_filename = "my_app_settings_example.ini"
    settings_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.TempLocation
    )
    QDir().mkpath(settings_dir)
    settings_file_path = os.path.join(settings_dir, settings_filename)

    if os.path.exists(settings_file_path):
        try:
            os.remove(settings_file_path)
        except Exception as e:
            logging.warning(
                f"Error removing existing settings file {settings_file_path}: {e}"
            )

    settings = QSettings(settings_file_path, QSettings.Format.IniFormat)

    manager = create_settings_manager(settings)

    window = MyWindow(manager=manager, settings_file_path=settings_file_path)

    setup_logging(window.log_window)

    manager.load()

    window._setup_file_watcher()
    window._update_settings_file_display()

    window.resize(700, 600)
    window.show()

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    exit_code = app.exec()

    if os.path.exists(settings_file_path):
        try:
            os.remove(settings_file_path)
        except Exception as e:
            logging.warning(f"Error removing settings file {settings_file_path}: {e}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
