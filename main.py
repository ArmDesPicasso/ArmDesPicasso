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
            
    @Slot()
def move_to_home(self):
    # Prüfen, ob die Swift-Verbindung vorhanden ist
    if self.swift is not None:
        # Geschwindigkeitsfaktor auf 1 setzen
        self.swift.set_speed_factor(1)
        # Gewünschte Home-Position definieren
        home_position = (200, 0, 150)
        speed = 50
        # Roboterarm zur Home-Position bewegen
        self.swift.set_position(*home_position, speed=speed)
        # Aktuelle Position abrufen
        self.get_position()

@Slot()
def open_canvas(self):
    # Zeichnungsszene erstellen
    scene = DrawingScene(self)
    scene.setBackgroundBrush(QColor("white"))
    # QGraphicsView für die Zeichnungsszene erstellen
    self.canvas_window = QGraphicsView(scene)
    self.canvas_window.setSceneRect(0, 0, 800, 600)  # Explizit das Szenenrechteck festlegen
    self.canvas_window.setWindowTitle("White Canvas")
    self.canvas_window.setGeometry(100, 100, 800, 600)
    self.canvas_window.setRenderHint(QPainter.Antialiasing)
    self.canvas_window.setInteractive(True)
    self.canvas_window.show()

@Slot()
def edge_detection(self):
    # Dialog zum Öffnen einer Bilddatei anzeigen
    image_file, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.xpm *.jpg *.bmp *.jpeg)")
    if image_file:
        self.process_image(image_file)

def process_image(self, image_file):
    # Bild laden und in Graustufen konvertieren
    image = cv2.imread(image_file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Kanten im Bild erkennen
    edges = cv2.Canny(gray, 100, 200)

    # QImage aus Kantenbild erstellen
    qt_img = QImage(edges.data, edges.shape[1], edges.shape[0], edges.strides[0], QImage.Format_Grayscale8)
    pixmap = QPixmap.fromImage(qt_img)

    # QGraphicsScene für das Kantenbild erstellen
    scene = QGraphicsScene(self)
    scene.setBackgroundBrush(QColor("white"))
    scene.addPixmap(pixmap)

    # QGraphicsView für die Kantenbildszene erstellen
    self.canvas_window = QGraphicsView(scene)
    self.canvas_window.setWindowTitle("Loaded Image")
    self.canvas_window.setGeometry(100, 100, 800, 600)
    self.canvas_window.setRenderHint(QPainter.Antialiasing)
    self.canvas_window.setInteractive(True)
    self.canvas_window.show()

    # Konturen im Kantenbild finden
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    self.contours = contours

def contours_to_points(self, contours):
    # Leere Liste für die Punkte erstellen
    points = []
    # Über alle Konturen iterieren
    for contour in contours:
        # Über alle Punkte in der aktuellen Kontur iterieren
        for point in contour:
            # Punkt zur Liste hinzufügen
            points.append((point[0][0], point[0][1]))
    return points

def distance(self, point1, point2):
    # Euklidischen Abstand zwischen zwei Punkten berechnen
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def send_points_to_swift(self, points):
    # Prüfen, ob die Swift-Verbindung vorhanden ist
    if self.swift is not None:
        # Zielbereich für die X- und Y-Koordinaten definieren
        target_x_range = (155, 250)
        target_y_range = (-75, 75)

        # Breite und Höhe des Zielbereichs berechnen
        target_width = target_x_range[1] - target_x_range[0]
        target_height = target_y_range[1] - target_y_range[0]

        # Seitenverhältnisse von Leinwand und Zielbereich berechnen
        canvas_aspect_ratio = self.canvas_width / self.canvas_height
        target_aspect_ratio = target_width / target_height

        # Skalierungsfaktoren für X- und Y-Koordinaten berechnen
        if canvas_aspect_ratio > target_aspect_ratio:
            scale_x = target_width / self.canvas_width
            scale_y = scale_x
        else:
            scale_y = target_height / self.canvas_height
            scale_x = scale_y

        # Z-Werte für Zeichnung und angehobene Position festlegen
        z_drawing = 38  # Z-Wert nach Bedarf anpassen
        z_lifted = 45  # Z-Wert für die angehobene Position anpassen
        speed = 5

        # Ersten Punkt in der Liste abrufen
        prev_point = points[0]
        # Roboterarm zur ersten Position bewegen (angehoben)
        self.swift.set_position(prev_point[0] * scale_x, prev_point[1] * scale_y, z_lifted, speed=speed)

        # Über die restlichen Punkte in der Liste iterieren
        for i in range(1, len(points)):
            curr_point = points[i]
            prev_point = points[i - 1]

            # Skalierte X- und Y-Koordinaten für aktuellen und vorherigen Punkt berechnen
            x_scaled = target_x_range[0] + curr_point[0] * scale_x
            y_scaled = target_y_range[0] + curr_point[1] * scale_y
            x_prev_scaled = target_x_range[0] + prev_point[0] * scale_x
            y_prev_scaled = target_y_range[0] + prev_point[1] * scale_y

            # Abstand zwischen aktuellem und vorherigem Punkt berechnen
            dist = self.distance((x_scaled, y_scaled), (x_prev_scaled, y_prev_scaled))

            # Schwellenwert für das Erkennen von Lücken festlegen
            gap_threshold = 10  # Schwellenwert nach Bedarf anpassen
                        if dist > gap_threshold:
                # Wenn der Abstand größer als der Schwellenwert ist, hebe den Roboterarm an
                self.swift.set_position(x_prev_scaled, y_prev_scaled, z_lifted, speed=speed)
                time.sleep(0.2)
                self.swift.set_position(x_scaled, y_scaled, z_lifted, speed=speed)
                time.sleep(0.2)

            # Bewege den Roboterarm zur aktuellen Position
            self.swift.set_position(x_scaled, y_scaled, z_drawing, speed=speed)
            time.sleep(0.01)  # Füge eine kurze Verzögerung zwischen den Bewegungen hinzu

        # Bewege den Roboterarm zurück zur Ausgangsposition, wenn alle Punkte abgearbeitet sind
        if self.swift is not None:
            self.swift.set_speed_factor(1)
            # Setze hier deine gewünschte Ausgangsposition
            home_position = (200, 0, 150)
            speed = 50
            self.swift.set_position(*home_position, speed=speed)
            self.get_position()

@Slot()
def export_points(self):
    # Überprüfe, ob das Canvas-Fenster vorhanden ist
    if self.canvas_window is not None:
        # Wenn die Szene eine DrawingScene ist, exportiere die Punkte daraus
        if isinstance(self.canvas_window.scene(), DrawingScene):
            points = self.canvas_window.scene().export_points()
        else:  # Wenn die Szene keine DrawingScene ist, handelt es sich um eine Bildszene
            points = self.contours_to_points(self.contours)
        print(f"Exporting points: {points}")
        self.send_points_to_swift(points)

def get_contours_from_image(self, image):
    # Konvertiere das Bild in Graustufen
    gray = image.convertToFormat(QImage.Format_Grayscale8)
    # Ermittle Kanten im Bild
    edges = cv2.cvtColor(np.array(gray), cv2.COLOR_GRAY2BGR)
    # Finde Konturen im Bild
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def grab_pencil(self):
    # Überprüfe, ob eine Verbindung zum Swift-Roboter besteht
    if self.swift is not None:
        # Definiere die tatsächlichen Koordinaten des Stifts
        pencil_position = (200, 45, 50)
        z_lifted = 150  # Passe den Z-Wert für die angehobene Position an
        speed = 100

        # Bewege den Roboterarm zur Stift-Position
        self.swift.set_polar(200, 45, 150, speed=speed)
        time.sleep(5)
        self.swift.set_polar(*pencil_position, speed=speed)
        time.sleep(5)

        # Schließe den Greifer, um den Stift zu greifen
        self.swift.set_gripper(True)
        time.sleep(10)

        # Hebe den Stift an
        self.swift.set_polar(pencil_position[0], pencil_position[1], z_lifted, speed=speed)
        time.sleep(5)
        self.swift.set_polar(200, 90, 150, speed=speed)
        time.sleep(5)

        
def main():
    # Erstelle eine QApplication-Instanz, die für Qt-Anwendungen benötigt wird.
    app = QApplication(sys.argv)

    # Erstelle eine Instanz der MainWindow-Klasse, die die Hauptbenutzeroberfläche darstellt.
    window = MainWindow()

    # Zeige das Hauptfenster der Anwendung an.
    window.show()

    # Führe die Qt-Anwendung aus und warte auf Benutzeraktionen.
    sys.exit(app.exec())


if __name__ == '__main__':
    # Wenn das Skript direkt ausgeführt wird (und nicht als Modul importiert wird),
    # rufe die 'main'-Funktion auf, um das Programm zu starten.
    main()

   

