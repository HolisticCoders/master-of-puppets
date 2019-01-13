from weakref import WeakKeyDictionary

from icarus.vendor.Qt import QtWidgets, QtCore
from icarus.core.rig import Rig
from icarus.ui.signals import publish, observe
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class ModulesPanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ModulesPanel, self).__init__(parent)
        self.setWindowTitle('Icarus Modules')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.tree_view = QtWidgets.QTreeView()
        layout.addWidget(self.tree_view)
        refresh_button = QtWidgets.QPushButton('Refresh')
        refresh_button.released.connect(self._refresh_model)
        layout.addWidget(refresh_button)

        self.model = ModulesModel()
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        selection = self.tree_view.selectionModel()
        selection.currentChanged.connect(self._on_current_changed)

        observe('module-created', self._refresh_model)
        observe('module-updated', self._refresh_model)

    def _refresh_model(self):
        self.model = ModulesModel()
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        selection = self.tree_view.selectionModel()
        selection.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, current, previous):
        module = current.internalPointer()
        publish('selected-module-changed', module)


class ModulesModel(QtCore.QAbstractItemModel):
    def __init__(self):
        super(ModulesModel, self).__init__()
        self._parent_modules_cache = WeakKeyDictionary()
        self.invalidate_cache()

    def invalidate_cache(self):
        """Refresh the cache."""
        rig = Rig()
        self.modules = rig.rig_modules
        for module in self.modules:
            self._parent_modules_cache[module] = module.parent_module

    def rowCount(self, parent):
        if not parent.isValid():
            return len([
                m for m in self.modules
                if self._parent_modules_cache[m] is None
            ])
        else:
            parent_module = parent.internalPointer()
            children = [
                m for m in self.modules
                if self._parent_modules_cache[m] is parent_module
            ]
            return len(children)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        module = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return module.node_name

    def index(self, row, column, parent):
        parent_module = parent.internalPointer() if parent.isValid() else None
        children = [
            m for m in self.modules
            if self._parent_modules_cache[m] is parent_module
        ]
        try:
            module = children[row]
        except IndexError:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, module)

    def parent(self, index):
        module = index.internalPointer()
        parent_module = self._parent_modules_cache[module]

        if not parent_module:
            return QtCore.QModelIndex()

        great_parent_module = self._parent_modules_cache[parent_module]
        great_children = [
            m for m in self.modules
            if self._parent_modules_cache[m] is great_parent_module
        ]
        row = great_children.index(parent_module)
        return self.createIndex(row, 0, parent_module)
