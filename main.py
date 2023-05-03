# Importiere erforderliche Standardbibliotheken
import sys  # Systemfunktionen und -parameter
import time  # Zeitbezogene Funktionen
import cv2  # OpenCV-Bibliothek für Computer Vision
import numpy as np  # Numerical Python, Bibliothek für mathematische Funktionen
import math  # Mathematische Funktionen

# Importiere erforderliche PySide6-Bibliotheken
from PySide6.QtCore import Slot, Qt, QRectF, QPointF, QLineF  # QtCore-Module für grundlegende Nicht-GUI-Funktionalität
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, QGridLayout, QDialog, \
    QGraphicsPathItem, QGraphicsLineItem  # QtWidgets-Module für GUI-Elemente
from PySide6.QtWidgets import QSlider, QHBoxLayout, QSizePolicy, QGraphicsView, QGraphicsScene, QFileDialog  # Weitere QtWidgets-Module
from PySide6.QtGui import QColor, QPainterPath, QPainter, QPen, QImage, QPixmap  # QtGui-Module für grafische Elemente

# Importiere uArm Swift-API-Bibliothek
from uarm.wrapper.swift_api import SwiftAPI
from uarm.utils.log import logger  # Logging-Funktionen von uArm


class DrawingScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path_item = None
        self.previous_pos = None
        self.lines = []  # Speichert die Linien-Items

    # Maus-Druck-Event-Handler
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Erstelle ein neues QGraphicsPathItem, wenn die linke Maustaste gedrückt wird
            self.current_path_item = QGraphicsPathItem()
            path = QPainterPath()
            path.moveTo(event.scenePos())  # Starte den Pfad an der aktuellen Mausposition
            self.current_path_item.setPath(path)
            self.addItem(self.current_path_item)
            self.previous_pos = event.scenePos()

    # Maus-Bewegungs-Event-Handler
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.previous_pos is not None:
            # Zeichne eine Linie von der vorherigen Position zur aktuellen Mausposition
            line = QGraphicsLineItem(QLineF(self.previous_pos, event.scenePos()))
            self.addItem(line)
            self.lines.append(line)  # Füge das Linien-Item zur Liste hinzu
            self.previous_pos = event.scenePos()

    # Maus-Loslass-Event-Handler
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Setze das aktuelle QGraphicsPathItem zurück, wenn die linke Maustaste losgelassen wird
            self.current_path_item = None

    # Exportiere die Punkte der gezeichneten Linien
    def export_points(self):
        points = []
        for line_item in self.lines:
            line = line_item.line()
            points.append((line.x1(), line.y1()))
            points.append((line.x2(), line.y2()))
        return points

      
class SetPositionDialog(QDialog):
    def __init__(self):
        super().__init__()
        # Erstelle QLabel und QLineEdit Widgets für X-, Y- und Z-Koordinaten
        self.x_label = QLabel("X:")
        self.x_input = QLineEdit()
        self.y_label = QLabel("Y:")
        self.y_input = QLineEdit()
        self.z_label = QLabel("Z:")
        self.z_input = QLineEdit()

        # Erstelle einen Submit-Button und verbinde das Klicksignal mit der accept-Methode
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept)

        # Erstelle ein QGridLayout und füge die Widgets hinzu
        layout = QGridLayout()
        layout.addWidget(self.x_label, 0, 0)
        layout.addWidget(self.x_input, 0, 1)
        layout.addWidget(self.y_label, 1, 0)
        layout.addWidget(self.y_input, 1, 1)
        layout.addWidget(self.z_label, 2, 0)
        layout.addWidget(self.z_input, 2, 1)
        layout.addWidget(self.submit_button, 3, 1)

        # Setze das Layout für diesen Dialog
        self.setLayout(layout)

    # Methode, um die eingegebenen Koordinaten als Tuple zurückzugeben
    def get_position(self):
        x = float(self.x_input.text())
        y = float(self.y_input.text())
        z = float(self.z_input.text())
        return x, y, z

      
# Hauptfenster-Klasse, die von QWidget erbt
class MainWindow(QWidget):
    def __init__(self):
        # Konstruktor der Basisklasse aufrufen
        super().__init__()

        # Schaltflächen und ihre Verbindung zu den entsprechenden Funktionen erstellen
        self.connect_button = QPushButton("Verbinde mit uArm")
        self.connect_button.clicked.connect(self.connect_to_uarm)
        self.disconnect_button = QPushButton("Trenne von uArm")
        self.disconnect_button.clicked.connect(self.disconnect_from_uarm)
        self.position_button = QPushButton("Position abrufen")
        self.position_button.clicked.connect(self.get_position)
        self.set_position_button = QPushButton("Position setzen")
        self.set_position_button.clicked.connect(self.set_position)
        self.open_canvas_button = QPushButton("Leinwand öffnen")
        self.open_canvas_button.clicked.connect(self.open_canvas)
        self.home_button = QPushButton("Zur Home-Position bewegen")
        self.home_button.clicked.connect(self.move_to_home)
        self.gripper_button = QPushButton("Greifer öffnen/schließen")
        self.gripper_button.clicked.connect(self.gripper)
        self.export_points_button = QPushButton("Punkte exportieren")
        self.export_points_button.clicked.connect(self.export_points)
        self.grab_pencil_button = QPushButton('Stift greifen', self)
        self.grab_pencil_button.clicked.connect(self.grab_pencil)
        self.edge_detection_button = QPushButton("Kantenerkennung")
        self.edge_detection_button.clicked.connect(self.edge_detection)

        # Positionsanzeige
        self.position_label = QLabel()

        # Layout erstellen und Widgets hinzufügen
        layout = QGridLayout()
        layout.addWidget(self.connect_button, 0, 0)
        layout.addWidget(self.disconnect_button, 0, 1)
        layout.addWidget(self.position_button, 1, 0)
        layout.addWidget(self.set_position_button, 1, 1)
        layout.addWidget(self.open_canvas_button, 2, 0)
        layout.addWidget(self.home_button, 2, 1)
        layout.addWidget(self.gripper_button, 3, 0)
        layout.addWidget(self.export_points_button, 3, 1)
        layout.addWidget(self.grab_pencil_button, 4, 0)
        layout.addWidget(self.edge_detection_button, 4, 1)
        layout.addWidget(self.position_label, 5, 0, 1, 2)

        # Layout auf das Hauptfenster anwenden
        self.setLayout(layout)

        # uArm-Swift-API-Objekt und Leinwand-Fenster initialisieren
        self.swift = None
        self.canvas_window = None

        # Schieberegler für X-, Y- und Z-Koordinaten erstellen und verbinden
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.valueChanged.connect(self.set_position_from_sliders)
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.valueChanged.connect(self.set_position_from_sliders)
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.valueChanged.connect(self.set_position_from_sliders)

        # Schiebereglerbereiche und -werte festlegen
        self.x_slider.setRange(150, 300)
        self.x_slider.setValue(150)
        self.y_slider.setRange(-100, 100)
        self.y_slider.setValue(0)
        self.z_slider.setRange(10, 200)
        self.z_slider.setValue(150)

                # Schiebereglerbeschriftungen erstellen
        self.x_slider_label = QLabel("X")
        self.y_slider_label = QLabel("Y")
        self.z_slider_label = QLabel("Z")

        # Schieberegler-Layout erstellen und Schieberegler hinzufügen
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
        layout.addLayout(slider_layout, 6, 0, 1, 2)

        # Initialisiere den Greiferzustand und die Arbeitsbereiche
        self.gripper_open = False
        self.x_range = (150, 300)  # Ersetze diese Werte durch den tatsächlichen X-Bereich deines Roboterarms
        self.y_range = (-150, 150)  # Ersetze diese Werte durch den tatsächlichen Y-Bereich deines Roboterarms
        self.canvas_width = 500  # Ersetze diesen Wert durch die tatsächliche Breite deiner Zeichenfläche
        self.canvas_height = 500  # Ersetze diesen Wert durch die tatsächliche Höhe deiner Zeichenfläche

    # Slot zum Verbinden mit dem uArm
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
        # self.swift.set_gripper(True)

    # Slot zum Trennen von dem uArm
    @Slot()
    def disconnect_from_uarm(self):
        if self.swift is not None:
            self.swift.set_gripper(False)
            self.swift.disconnect()

    # Slot zum Umschalten des Greifers
    @Slot()
    def gripper(self):
        if self.swift is not None:
            self.gripper_open = not self.gripper_open
            self.swift.set_gripper(self.gripper_open)

    # Slot zum Abrufen der aktuellen Position
    @Slot()
    def get_position(self):
        if self.swift is not None:
            pos = self.swift.get_position()
            self.position_label.setText(f"Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

    # Slot zum Festlegen einer neuen Position
    @Slot()
    def set_position(self):
        if self.swift is not None:
            dialog = SetPositionDialog()
            result = dialog.exec()
            if result == QDialog.Accepted:
                pos = dialog.get_position()
                self.swift.set_position(*pos)
                self.get_position()

    # Slot zum Festlegen einer Position mit Schiebereglern
    @Slot()
    def set_position_from_sliders(self):
        if self.swift is not None:
            x = self.x_slider.value()
            y = self.y_slider.value()
            z = self.z_slider.value()
            self.swift.set_position(x, y, z)
            self.get_position()
            
    

