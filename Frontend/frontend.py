import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsItem, QDockWidget, QListWidget, QListWidgetItem,
    QAction, QFileDialog
)
from PyQt5.QtGui import QBrush, QColor, QDrag, QPainter, QPen, QPainterPath
from PyQt5.QtCore import Qt, QMimeData, QPointF

class ConnectionPort(QGraphicsEllipseItem):
    def __init__(self, parent, offset):
        r = 4
        super().__init__(-r, -r, 2*r, 2*r, parent)
        self.setBrush(QBrush(QColor("black")))
        self.setFlag(QGraphicsEllipseItem.ItemSendsScenePositionChanges)
        self.offset = offset
        self.setPos(offset)
        self.wires = []

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            for wire in self.wires:
                wire.update_position()
        return super().itemChange(change, value)

class ComponentItem(QGraphicsRectItem):
    def __init__(self, component_type):
        super().__init__(0, 0, 60, 30)
        self.component_type = component_type
        self.value = {
            'Resistor': '1k',
            'Capacitor': '1u',
            'Inductor': '1m',
            'VoltageSource': '5'
        }.get(component_type, '1')
        self.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.ports = [ConnectionPort(self, QPointF(0, 15)), ConnectionPort(self, QPointF(60, 15))]

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black, 2))
        bbox = self.rect()
        x0 = bbox.x()
        y0 = bbox.y() + bbox.height() / 2
        width = bbox.width()

        if self.component_type == 'Resistor':
            terminal = 10
            zig_start = x0 + terminal
            zig_end = x0 + width - terminal
            # start terminal
            painter.drawLine(QPointF(x0, y0), QPointF(zig_start, y0))
            # zig-zag
            path = QPainterPath(QPointF(zig_start, y0))
            seg = (zig_end - zig_start) / 6
            for i in range(6):
                x = zig_start + seg * (i + 1)
                y = y0 + (10 if i % 2 == 0 else -10)
                path.lineTo(x, y)
            painter.drawPath(path)
            # end terminal
            painter.drawLine(QPointF(zig_end, y0), QPointF(x0 + width, y0))

        elif self.component_type == 'Capacitor':
            x1 = x0 + width / 3
            x2 = x0 + 2 * width / 3
            y = y0
            painter.drawLine(QPointF(x1, y - 15), QPointF(x1, y + 15))
            painter.drawLine(QPointF(x2, y - 15), QPointF(x2, y + 15))
            painter.drawLine(QPointF(x0, y), QPointF(x1, y))
            painter.drawLine(QPointF(x2, y), QPointF(x0 + width, y))

        elif self.component_type == 'Inductor':
            path = QPainterPath(QPointF(x0, y0))
            r = bbox.height() / 2
            turns = 4
            seg = width / turns
            for i in range(turns):
                cx = x0 + seg * i + seg / 2
                path.arcTo(cx - r, y0 - r, 2 * r, 2 * r, 180, -180)
            painter.drawPath(path)

        elif self.component_type == 'VoltageSource':
            cx = x0 + width / 2
            cy = y0
            r = min(width, bbox.height()) / 2 - 5
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawText(QPointF(cx - 4, cy - r - 5), '+')
            painter.drawText(QPointF(cx - 4, cy + r + 15), '-')
            painter.drawLine(QPointF(x0, cy), QPointF(cx - r, cy))
            painter.drawLine(QPointF(cx + r, cy), QPointF(x0 + width, cy))

    def mouseDoubleClickEvent(self, event):
        print(f"Properties: {self.component_type}, value={self.value}")
        super().mouseDoubleClickEvent(event)

class WireItem(QGraphicsPathItem):
    def __init__(self, port1, port2):
        super().__init__()
        self.start_port = port1
        self.end_port = port2
        self.setPen(QPen(Qt.black, 2))
        self.setZValue(-1)
        port1.wires.append(self)
        port2.wires.append(self)
        self.update_position()

    def update_position(self):
        p1 = self.start_port.scenePos()
        p2 = self.end_port.scenePos()
        path = QPainterPath(p1)
        mid = QPointF(p2.x(), p1.y())
        path.lineTo(mid)
        path.lineTo(p2)
        self.setPath(path)

class GraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing)
        self.setAcceptDrops(True)
        self.temp_path = None
        self.start_port = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    def dropEvent(self, event):
        comp = event.mimeData().text()
        pos = self.mapToScene(event.pos())
        item = ComponentItem(comp)
        item.setPos(pos)
        self.scene().addItem(item)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        items = self.scene().items(pos)
        port = next((i for i in items if isinstance(i, ConnectionPort)), None)
        if port:
            self.start_port = port
            self.temp_path = QGraphicsPathItem()
            self.temp_path.setPen(QPen(Qt.red, 1, Qt.DashLine))
            p = port.scenePos()
            path = QPainterPath(p)
            path.lineTo(p)
            self.temp_path.setPath(path)
            self.scene().addItem(self.temp_path)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.temp_path and self.start_port:
            p = self.mapToScene(event.pos())
            start = self.temp_path.path().elementAt(0)
            new_path = QPainterPath(QPointF(start.x, start.y))
            mid = QPointF(p.x(), start.y)
            new_path.lineTo(mid)
            new_path.lineTo(p)
            self.temp_path.setPath(new_path)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_path and self.start_port:
            pos = self.mapToScene(event.pos())
            items = self.scene().items(pos)
            from_port = self.start_port
            self.start_port = None
            self.scene().removeItem(self.temp_path)
            self.temp_path = None
            port = next((i for i in items if isinstance(i, ConnectionPort) and i is not from_port), None)
            if port:
                wire = WireItem(from_port, port)
                self.scene().addItem(wire)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_R:
            for item in self.scene().selectedItems():
                if isinstance(item, ComponentItem):
                    item.setRotation(item.rotation() + 90)
        else:
            super().keyPressEvent(event)

class SimulatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analog Circuit Simulator")
        self.resize(800, 600)
        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene)
        self.setCentralWidget(self.view)
        self.init_palette()
        self.init_actions()

    def init_palette(self):
        dock = QDockWidget("Components", self)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        lw = QListWidget()
        for c in ['Resistor', 'Capacitor', 'Inductor', 'VoltageSource']:
            it = QListWidgetItem(c)
            it.setData(Qt.UserRole, c)
            lw.addItem(it)
        lw.setDragEnabled(True)
        lw.mouseMoveEvent = lambda e: self.start_drag(e, lw)
        dock.setWidget(lw)

    def init_actions(self):
        tb = self.addToolBar("Tools")
        sa = QAction("Simulate", self)
        sa.triggered.connect(self.generate_netlist)
        tb.addAction(sa)
        da = QAction("Delete", self)
        da.triggered.connect(self.delete_selected)
        tb.addAction(da)

    def start_drag(self, event, widget):
        item = widget.currentItem()
        if not item:
            return
        mime = QMimeData()
        mime.setText(item.data(Qt.UserRole))
        d = QDrag(widget)
        d.setMimeData(mime)
        d.exec_(Qt.CopyAction)

    def delete_selected(self):
        for item in list(self.scene().selectedItems()):
            if isinstance(item, ConnectionPort):
                for w in list(item.wires):
                    self.scene().removeItem(w)
                    w.start_port.wires.remove(w)
                    w.end_port.wires.remove(w)
            self.scene().removeItem(item)

    def generate_netlist(self):
        parent = {}
        def find(x):
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        def union(a, b):
            parent[find(a)] = find(b)

        ports = [i for i in self.scene().items() if isinstance(i, ConnectionPort)]
        for i in self.scene().items():
            if isinstance(i, WireItem):
                union(id(i.start_port), id(i.end_port))

        nodes = {}
        nid = 1
        for p in ports:
            root = find(id(p))
            if root not in nodes:
                nodes[root] = nid
                nid += 1

        lines = []
        cnt = {}
        for i in self.scene().items():
            if isinstance(i, ComponentItem):
                t = i.component_type[0].upper()
                cnt.setdefault(t, 0)
                cnt[t] += 1
                name = f"{t}{cnt[t]}"
                n1 = nodes.get(find(id(i.ports[0])), 0)
                n2 = nodes.get(find(id(i.ports[1])), 0)
                lines.append(f"{name} {n1} {n2} {i.value}")

        path, _ = QFileDialog.getSaveFileName(self, "Save Netlist", "circuit.net", "Netlist Files (*.net)")
        if path:
            with open(path, 'w') as f:
                f.write("* Generated by Analog Circuit Simulator\n")
                f.write("\n".join(lines))
            print(f"Netlist saved to {path}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = SimulatorWindow()
    w.show()
    sys.exit(app.exec_())
