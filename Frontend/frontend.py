import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QDockWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QBrush, QColor, QDrag
from PyQt5.QtCore import Qt, QMimeData, QPointF

class ComponentItem(QGraphicsRectItem):
    """
    A basic rectangular component that can be moved and selected.
    """
    def __init__(self, component_type, width=60, height=30):
        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(QColor("lightgray")))
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.component_type = component_type

    def mouseDoubleClickEvent(self, event):
        # Placeholder for opening a properties dialog
        print(f"Open properties for {self.component_type}")
        super().mouseDoubleClickEvent(event)

class GraphicsView(QGraphicsView):
    """
    A custom QGraphicsView that accepts drops for creating components.
    """
    def __init__(self, scene):
        super().__init__(scene)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        comp_type = event.mimeData().text()
        pos = self.mapToScene(event.pos())
        item = ComponentItem(comp_type)
        item.setPos(pos)
        self.scene().addItem(item)
        event.acceptProposedAction()

class SimulatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analog Circuit Simulator")
        self.resize(800, 600)

        # Create the graphics scene and view
        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene)
        self.setCentralWidget(self.view)

        # Initialize the component palette
        self.init_palette()

    def init_palette(self):
        dock = QDockWidget("Components", self)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        list_widget = QListWidget()

        # Define available components
        for comp in ["Resistor", "Capacitor", "Inductor", "VoltageSource"]:
            item = QListWidgetItem(comp)
            item.setData(Qt.UserRole, comp)
            list_widget.addItem(item)

        # Enable dragging from the palette
        list_widget.setDragEnabled(True)
        list_widget.mouseMoveEvent = lambda e: self.start_drag(e, list_widget)
        dock.setWidget(list_widget)

    def start_drag(self, event, widget):
        item = widget.currentItem()
        if not item:
            return
        mime = QMimeData()
        comp_type = item.data(Qt.UserRole)
        mime.setText(comp_type)
        drag = QDrag(widget)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)

def main():
    app = QApplication(sys.argv)
    window = SimulatorWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
