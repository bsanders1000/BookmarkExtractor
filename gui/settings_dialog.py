from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.settings_manager = settings_manager

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("OpenAI API Key:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(self.settings_manager.get_api_key())
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.api_key_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.settings_manager.set_api_key(self.api_key_edit.text())
        super().accept()