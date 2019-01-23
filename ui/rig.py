from weakref import WeakKeyDictionary

from icarus.vendor.Qt import QtWidgets, QtCore
from icarus.core.rig import Rig
from icarus.ui.signals import publish, subscribe
from icarus.ui.commands import build_rig, unbuild_rig, publish_rig


class RigPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RigPanel, self).__init__(parent)
        self.setObjectName('icarus_rig_panel')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Rig Panel')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.modules_group = QtWidgets.QGroupBox('Modules')
        self.actions_group = QtWidgets.QGroupBox('Actions')

        layout.addWidget(self.modules_group)
        layout.addWidget(self.actions_group)

        modules_layout = QtWidgets.QVBoxLayout()
        actions_layout = QtWidgets.QHBoxLayout()

        self.modules_group.setLayout(modules_layout)
        self.actions_group.setLayout(actions_layout)

        self.tree_view = QtWidgets.QTreeView()
        modules_layout.addWidget(self.tree_view)

        refresh_button = QtWidgets.QPushButton('Refresh')
        build_button = QtWidgets.QPushButton('Build Rig')
        unbuild_button = QtWidgets.QPushButton('Unbuild Rig')
        publish_button = QtWidgets.QPushButton('Publish Rig')

        actions_layout.addWidget(refresh_button)
        actions_layout.addWidget(build_button)
        actions_layout.addWidget(unbuild_button)
        actions_layout.addWidget(publish_button)

        refresh_button.released.connect(self._refresh_model)
        build_button.released.connect(build_rig)
        unbuild_button.released.connect(unbuild_rig)
        publish_button.released.connect(publish_rig)

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

        # Find the index of the new module.
        # NOTE: maybe optimize this part, and keep the same
        # model for the whole session, instead of discarding
        # it for any module added/deleted/changed.
        if module:
            index = self._find_index(module)
            if index:
                self.tree_view.selectionModel().setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.SelectCurrent,
                )

    def _find_index(self, module, index=QtCore.QModelIndex()):
        """Return a Qt index to ``module``.

        If there is no modules model yet, or the module cannot be
        found, return ``None``.

        A matching index is an index containing a module of the same
        :attr:`icarus.core.module.RigModule.node_name` as the passed
        module.

        :param module: Module to find the index of.
        :param index: Parent index of the search, since we are in a
                      tree view.
        :type module: icarus.core.module.RigModule
        :type index: PySide2.QtCore.QModelIndex
        :rtype: PySide2.QtCore.QModelIndex
        """
        if not self.model:
            return None
        name = module.node_name
        for i in xrange(self.model.rowCount(index)):
            child = self.model.index(i, 0, index)
            if child.internalPointer().node_name == name:
                return child
            _index = self._find_index(module, child)
            if _index:
                return _index

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
