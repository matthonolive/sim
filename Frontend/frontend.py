import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsItem, QDockWidget, QListWidget, QListWidgetItem,
    QAction, QFileDialog, QInputDialog
)
from PyQt5.QtGui import QBrush, QColor, QPen, QPainterPath, QPainter, QDrag
from PyQt5.QtCore import Qt, QPointF, QMimeData

class ConnectionPort(QGraphicsEllipseItem):
    def __init__(self, parent, offset):
        super().__init__(-4, -4, 8, 8, parent)
        self.setBrush(QBrush(Qt.black))
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
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
        self.value = {'Resistor': '1k', 'Capacitor': '1u', 'Inductor': '1m', 'VoltageSource': '5'}[component_type]
        self.setBrush(QBrush(Qt.transparent))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.ports = [ConnectionPort(self, QPointF(0, 15)), ConnectionPort(self, QPointF(60, 15))]

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black, 2))
        rect = self.rect()
        x0, y0 = rect.x(), rect.y() + rect.height() / 2
        w = rect.width()

        if self.component_type == 'Resistor':
            term = 10
            painter.drawLine(QPointF(x0, y0), QPointF(x0+term, y0))
            painter.drawLine(QPointF(x0+w-term, y0), QPointF(x0+w, y0))
            start, end = x0+term, x0+w-term
            segments, amp = 6, 6
            seg_w = (end-start)/segments
            path = QPainterPath(QPointF(start, y0))
            for i in range(segments):
                xi = start + seg_w*(i+1)
                yi = y0 + (amp if i%2==0 else -amp)
                if i == segments - 1:
                    path.lineTo(xi, y0)
                else:
                    path.lineTo(xi, yi)
            painter.drawPath(path)

        elif self.component_type == 'Capacitor':
            x1, x2 = x0 + w/3, x0 + 2*w/3
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y0))
            painter.drawLine(QPointF(x2, y0), QPointF(x0+w, y0))
            painter.drawLine(QPointF(x1, y0-15), QPointF(x1, y0+15))
            painter.drawLine(QPointF(x2, y0-15), QPointF(x2, y0+15))

        elif self.component_type == 'Inductor':
            painter.drawLine(QPointF(x0, y0), QPointF(x0+10, y0))
            painter.drawLine(QPointF(x0+w-10, y0), QPointF(x0+w, y0))
            path = QPainterPath(QPointF(x0+10, y0))
            r = rect.height()/2
            turns, seg = 4, (w-20)/4
            for i in range(turns):
                cx = x0+10 + seg*i + seg/2
                path.arcTo(cx-r, y0-r, 2*r, 2*r, 180, -180)
            painter.drawPath(path)

        elif self.component_type == 'VoltageSource':
            cx, cy = x0 + w/2, y0
            r = min(w, rect.height())/2 - 5
            painter.drawLine(QPointF(x0, cy), QPointF(cx-r, cy))
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.drawLine(QPointF(cx+r, cy), QPointF(x0+w, cy))
            for idx, sign in enumerate(['+', '-']):
                off = self.ports[idx].offset
                painter.drawText(QPointF(off.x()-4, off.y()-12), sign)

        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(QPointF(x0+5, rect.y()+rect.height()+12), self.value)

class WireItem(QGraphicsPathItem):
    def __init__(self, p1, p2):
        super().__init__()
        self.start_port, self.end_port = p1, p2
        self.setPen(QPen(Qt.black, 2))
        self.setZValue(-1)
        p1.wires.append(self)
        p2.wires.append(self)
        self.update_position()

    def update_position(self):
        p1, p2 = self.start_port.scenePos(), self.end_port.scenePos()
        path = QPainterPath(p1)
        mid = QPointF(p2.x(), p1.y())
        path.lineTo(mid)
        path.lineTo(p2)
        self.setPath(path)

class GraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing)
        self.setAcceptDrops(True)
        self.temp_path, self.start_port = None, None

    def dragEnterEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dropEvent(self, e):
        comp = e.mimeData().text()
        item = ComponentItem(comp)
        item.setPos(self.mapToScene(e.pos()))
        self.scene().addItem(item)
        e.acceptProposedAction()

    def mousePressEvent(self, e):
        pos = self.mapToScene(e.pos())
        for itm in self.scene().items(pos):
            if isinstance(itm, ConnectionPort):
                self.start_port = itm
                self.temp_path = QGraphicsPathItem()
                self.temp_path.setPen(QPen(Qt.red,1,Qt.DashLine))
                self.scene().addItem(self.temp_path)
                p = itm.scenePos()
                self.temp_path.setPath(QPainterPath(p))
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.temp_path and self.start_port:
            p = self.mapToScene(e.pos())
            start = self.temp_path.path().elementAt(0)
            newp = QPainterPath(QPointF(start.x, start.y))
            newp.lineTo(QPointF(p.x(), start.y))
            newp.lineTo(p)
            self.temp_path.setPath(newp)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.temp_path and self.start_port:
            to_port=None
            pos = self.mapToScene(e.pos())
            for itm in self.scene().items(pos):
                if isinstance(itm, ConnectionPort) and itm is not self.start_port:
                    to_port=itm; break
            self.scene().removeItem(self.temp_path)
            self.temp_path=None
            if to_port:
                self.scene().addItem(WireItem(self.start_port,to_port))
            self.start_port=None
        else:
            super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key()==Qt.Key_R:
            for itm in self.scene().selectedItems():
                if isinstance(itm, ComponentItem): itm.setRotation(itm.rotation()+90)
        else: super().keyPressEvent(e)

class SimulatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analog Circuit Simulator")
        self.setGeometry(100,100,800,600)
        self.scene, self.view = QGraphicsScene(), GraphicsView(QGraphicsScene())
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)
        self.init_palette(); self.init_actions()

    def init_palette(self):
        dock = QDockWidget("Components", self)
        lw = QListWidget(); lw.setDragEnabled(True)
        for c in ['Resistor','Capacitor','Inductor','VoltageSource']:
            it=QListWidgetItem(c); it.setData(Qt.UserRole,c); lw.addItem(it)
        lw.mouseMoveEvent=lambda e: self.start_drag(e,lw)
        dock.setWidget(lw); self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def init_actions(self):
        tb=self.addToolBar("Tools")
        a=QAction("Simulate",self); a.triggered.connect(self.generate_netlist); tb.addAction(a)
        d=QAction("Delete",self); d.triggered.connect(self.delete_selected); tb.addAction(d)

    def start_drag(self, e, w):
        it=w.currentItem()
        if it:
            m=QMimeData(); m.setText(it.data(Qt.UserRole))
            d=QDrag(w); d.setMimeData(m); d.exec_(Qt.CopyAction)

    def delete_selected(self):
        for itm in list(self.scene.selectedItems()):
            if isinstance(itm, ConnectionPort):
                for w in list(itm.wires):
                    self.scene.removeItem(w)
                    w.start_port.wires.remove(w)
                    w.end_port.wires.remove(w)
            self.scene.removeItem(itm)

    def generate_netlist(self):
            parent = {}

            def find(x):
                parent.setdefault(x, x)
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(a, b):
                parent.setdefault(a, a)
                parent.setdefault(b, b)
                parent[find(a)] = find(b)

            # now use find/union to cluster ports into nodes…
            ports = [i for i in self.scene.items() if isinstance(i, ConnectionPort)]
            for itm in self.scene.items():
                if isinstance(itm, WireItem):
                    union(id(itm.start_port), id(itm.end_port))

            # assign node numbers
            nodes = {}
            nid = 1
            for p in ports:
                root = find(id(p))
                if root not in nodes:
                    nodes[root] = nid
                    nid += 1

            # build netlist lines
            lines = []
            cnt = {}
            for comp in self.scene.items():
                if isinstance(comp, ComponentItem):
                    t = comp.component_type[0].upper()
                    cnt.setdefault(t, 0)
                    cnt[t] += 1
                    name = f"{t}{cnt[t]}"
                    n1 = nodes.get(find(id(comp.ports[0])), 0)
                    n2 = nodes.get(find(id(comp.ports[1])), 0)
                    lines.append(f"{name} {n1} {n2} {comp.value}")

            path, _ = QFileDialog.getSaveFileName(self, "Save Netlist", "circuit.net", "Netlist Files (*.net)")
            if path:
                with open(path, 'w') as f:
                    f.write("* Generated by Analog Circuit Simulator\n")
                    f.write("\n".join(lines))
                print(f"Netlist saved to {path}")

if __name__=='__main__':
    app=QApplication(sys.argv)
    w=SimulatorWindow(); w.show(); sys.exit(app.exec_())
