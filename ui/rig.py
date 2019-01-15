from weakref import WeakKeyDictionary

from icarus.vendor.Qt import QtWidgets, QtCore
from icarus.core.rig import Rig
from icarus.ui.signals import publish, subscribe, unsubscribe
from icarus.ui.commands import build_rig, unbuild_rig
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class RigPanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RigPanel, self).__init__(parent)
        self.setObjectName('icarus_rig_panel')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Icarus Rig Panel')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.modules_group = QtWidgets.QGroupBox('Modules')
        self.actions_group = QtWidgets.QGroupBox('Actions')

        layout.addWidget(self.modules_group)
        layout.addWidget(self.actions_group)

        modules_layout = QtWidgets.QVBoxLayout()
        actions_layout = QtWidgets.QVBoxLayout()

        self.modules_group.setLayout(modules_layout)
        self.actions_group.setLayout(actions_layout)

        self.tree_view = QtWidgets.QTreeView()
        modules_layout.addWidget(self.tree_view)

        refresh_button = QtWidgets.QPushButton('Refresh')
        build_button = QtWidgets.QPushButton('Build Rig')
        unbuild_button = QtWidgets.QPushButton('Unbuild Rig')

        actions_layout.addWidget(refresh_button)
        actions_layout.addWidget(build_button)
        actions_layout.addWidget(unbuild_button)

        refresh_button.released.connect(self._refresh_model)
        build_button.released.connect(build_rig)
        unbuild_button.released.connect(unbuild_rig)

        self.model = ModulesModel()
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        selection = self.tree_view.selectionModel()
        selection.currentChanged.connect(self._on_current_changed)

        subscribe('module-created', self._refresh_model)
        subscribe('module-updated', self._refresh_model)
        subscribe('module-deleted', self._refresh_model)

    def _refresh_model(self, module=None):
        self.model = ModulesModel()
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        selection = self.tree_view.selectionModel()
        selection.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, current, previous):
        module = current.internalPointer()
        publish('selected-module-changed', module)

    def close(self):
        unsubscribe('module-created', self._refresh_model)
        unsubscribe('module-updated', self._refresh_model)
        unsubscribe('module-deleted', self._refresh_model)
        return super(RigPanel, self).close()


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
