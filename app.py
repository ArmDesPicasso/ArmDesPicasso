import sys
import time

from PySide6.QtCore import Slot, Qt, QRectF, QPointF
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QGridLayout, QDialog, \
    QGraphicsPathItem
from PySide6.QtWidgets import QSlider, QHBoxLayout, QSizePolicy, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QColor, QPainterPath, QPainter, QPen
from uarm.wrapper.swift_api import SwiftAPI
from uarm.utils.log import logger

logger.setLevel(logger.VERBOSE)


class DrawingScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path_item = None
        self.previous_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.current_path_item = QGraphicsPathItem()
            path = QPainterPath()
            path.moveTo(event.scenePos())
            self.current_path_item.setPath(path)
            self.addItem(self.current_path_item)
            self.previous_pos = event.scenePos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.current_path_item is not None:
            path = self.current_path_item.path()
            path.lineTo(event.scenePos())
            self.current_path_item.setPath(path)
            self.previous_pos = event.scenePos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.current_path_item = None


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
        self.open_canvas_button = QPushButton("Open Canvas")
        self.open_canvas_button.clicked.connect(self.open_canvas)
        self.home_button = QPushButton("Move to Home")
        self.home_button.clicked.connect(self.move_to_home)
        self.position_label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.position_button)
        layout.addWidget(self.set_position_button)
        layout.addWidget(self.open_canvas_button)
        layout.addWidget(self.home_button)
        layout.addWidget(self.position_label)
        self.setLayout(layout)
        self.swift = None
        # Add a variable to store the canvas window
        self.canvas_window = None

        #Ab hier neuer Code

        # Add sliders
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.valueChanged.connect(self.set_position_from_sliders)
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.valueChanged.connect(self.set_position_from_sliders)
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.valueChanged.connect(self.set_position_from_sliders)

        # Set slider ranges (customize these as needed)
        self.x_slider.setRange(100, 200)
        self.x_slider.setValue(150)
        self.y_slider.setRange(-100, 100)
        self.y_slider.setValue(0)
        self.z_slider.setRange(10, 200)
        self.z_slider.setValue(150)

        # Add slider labels
        self.x_slider_label = QLabel("X")
        self.y_slider_label = QLabel("Y")
        self.z_slider_label = QLabel("Z")

        # Add sliders and labels to the layout
        slider_layout = QVBoxLayout()
        x_row = QHBoxLayout()
        x_row.addWidget(self.x_slider_label)
        x_row.addWidget(self.x_slider)
        slider_layout.addLayout(x_row)

        y_row = QHBoxLayout()
        y_row.addWidget(self.y_slider_label)
        y_row.addWidget(self.y_slider)
        slider_layout.addLayout(y_row)

        z_row = QHBoxLayout()
        z_row.addWidget(self.z_slider_label)
        z_row.addWidget(self.z_slider)
        slider_layout.addLayout(z_row)

        layout.addLayout(slider_layout)

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
        self.swift.set_gripper(True)

    @Slot()
    def disconnect_from_uarm(self):
        if self.swift is not None:
            self.swift.set_gripper(False)
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

    @Slot()
    def set_position_from_sliders(self):
        if self.swift is not None:
            x = self.x_slider.value()
            y = self.y_slider.value()
            z = self.z_slider.value()
            speed = 5
            self.swift.set_position(x, y, z, speed=speed)
            self.get_position()

    @Slot()
    def open_canvas(self):
        self.canvas_window = QGraphicsView()
        scene = QGraphicsScene(self)
        scene.setBackgroundBrush(QColor("white"))
        self.canvas_window.setScene(scene)
        self.canvas_window.setWindowTitle("White Canvas")
        self.canvas_window.setGeometry(100, 100, 800, 600)
        self.canvas_window.show()

    @Slot()
    def move_to_home(self):
        if self.swift is not None:
            # Set your desired home position here
            home_position = (150, 0, 150)
            self.swift.set_position(*home_position)
            self.get_position()

    @Slot()
    def open_canvas(self):
        scene = DrawingScene(self)
        scene.setBackgroundBrush(QColor("white"))
        self.canvas_window = QGraphicsView(scene)
        self.canvas_window.setWindowTitle("White Canvas")
        self.canvas_window.setGeometry(100, 100, 800, 600)
        self.canvas_window.setRenderHint(QPainter.Antialiasing)
        self.canvas_window.setInteractive(True)
        self.canvas_window.show()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()



