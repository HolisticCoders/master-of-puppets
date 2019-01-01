from icarus.vendor.Qt import QtWidgets, QtGui, QtCore
from icarus.core.rig import Rig
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class ModulesPanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ModulesPanel, self).__init__(parent)
        self.setWindowTitle('Icarus Modules') 

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.tree_view = QtWidgets.QTreeView()
        layout.addWidget(self.tree_view)

        rig = Rig()
        modules = rig.rig_modules

        self.model = ModulesModel(modules)
        self.tree_view.setModel(self.model)


class ModulesModel(QtCore.QAbstractItemModel):
    def __init__(self, modules):
        super(ModulesModel, self).__init__()
        self.modules = modules

    def rowCount(self, parent):
        if not parent.isValid():
            return len([m for m in self.modules if m.parent_module is None])
        else:
            parent_module = parent.internalPointer()
            children = [m for m in self.modules if m.parent_module is parent_module]
            return len(children)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        module = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return module.node_name

    def index(self, row, column, parent):
        parent_module = parent.internalPointer() if parent.isValid() else None
        children = [m for m in self.modules if m.parent_module is parent_module]
        module = children[row]
        return self.createIndex(row, column, module)

    def parent(self, index):
        module = index.internalPointer()
        parent_module = module.parent_module

        if not parent_module:
            return QtCore.QModelIndex()

        great_parent_module = parent_module.parent_module
        great_children = [m for m in self.modules if m.parent_module is great_parent_module]
        row = great_children.index(parent_module)
        return self.createIndex(row, 0, parent_module)

