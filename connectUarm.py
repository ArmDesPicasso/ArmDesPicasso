import sys
import time

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QGridLayout, QDialog
from uarm.wrapper.swift_api import SwiftAPI
from uarm.utils.log import logger

logger.setLevel(logger.VERBOSE)


class SetPositionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.x_label = QLabel("X:")
        self.x_input = QLineEdit()
        self.y_label = QLabel("Y:")
        self.y_input = QLineEdit()
        self.z_label = QLabel("Z:")
        self.z_input = QLineEdit()
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept)
        layout = QGridLayout()
        layout.addWidget(self.x_label, 0, 0)
        layout.addWidget(self.x_input, 0, 1)
        layout.addWidget(self.y_label, 1, 0)
        layout.addWidget(self.y_input, 1, 1)
        layout.addWidget(self.z_label, 2, 0)
        layout.addWidget(self.z_input, 2, 1)
        layout.addWidget(self.submit_button, 3, 1)
        self.setLayout(layout)

    def get_position(self):
        x = float(self.x_input.text())
        y = float(self.y_input.text())
        z = float(self.z_input.text())
        return x, y, z


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.connect_button = QPushButton("Connect to uArm")
        self.connect_button.clicked.connect(self.connect_to_uarm)
        self.disconnect_button = QPushButton("Disconnect from uArm")
        self.disconnect_button.clicked.connect(self.disconnect_from_uarm)
        self.position_button = QPushButton("Get Position")
        self.position_button.clicked.connect(self.get_position)
        self.set_position_button = QPushButton("Set Position")
        self.set_position_button.clicked.connect(self.set_position)
        self.position_label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.position_button)
        layout.addWidget(self.set_position_button)
        layout.addWidget(self.position_label)
        self.setLayout(layout)
        self.swift = None

    @Slot()
    def connect_to_uarm(self):
        accessed = False
        while not accessed:
            try:
                self.swift = SwiftAPI(port="COM3", callback_thread_pool_size=1)
                accessed = True
            except Exception as e:
                print(str(e))
                time.sleep(0.2)

        print('device info: ')
        print(self.swift.get_device_info())

        self.swift.connect()

    @Slot()
    def disconnect_from_uarm(self):
        if self.swift is not None:
            self.swift.disconnect()

    @Slot()
    def get_position(self):
        if self.swift is not None:
            pos = self.swift.get_position()
            self.position_label.setText(f"Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

    @Slot()
    def set_position(self):
        if self.swift is not None:
            dialog = SetPositionDialog()
            result = dialog.exec()
            if result == QDialog.Accepted:
                pos = dialog.get_position()
                self.swift.set_position(*pos)
                self.get_position()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
