import pdb
from collections import defaultdict
from weakref import WeakKeyDictionary, WeakSet

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
        pointer = current.internalPointer()
        publish('selected-module-changed', pointer)


class ModulesModel(QtCore.QAbstractItemModel):
    """A model storing modules and their deform joints.

    In this model, joints are stored as :class:`str` instances,
    and modules as :class:`icarus.core.module.RigModule`.
    """

    def __init__(self, parent=None):
        super(ModulesModel, self).__init__(parent)
        self.invalidate_cache()

    def invalidate_cache(self):
        """Refresh the cache."""
        rig = Rig()
        self.modules = rig.rig_modules

        self._top_level_modules = []
        self._joints_parent_module = {}
        self._joints_child_modules = defaultdict(list)
        self._modules_parent_joint = {}
        self._modules_child_joints = defaultdict(list)

        for module in self.modules:
            parent = module.parent_joint.get()
            self._modules_parent_joint[module] = parent
            self._joints_child_modules[parent].append(module)
            if parent is None:
                self._top_level_modules.append(module)
            for joint in module.deform_joints:
                self._joints_parent_module[joint] = module
                self._modules_child_joints[module].append(joint)

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self._top_level_modules)
        else:
            pointer = parent.internalPointer()
            if isinstance(pointer, basestring):
                # We got ourselves a joint.
                return len(self._joints_child_modules[pointer])
            elif pointer:
                # We found a module.
                return len(self._modules_child_joints[pointer])
        return 0

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None
        pointer = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            if isinstance(pointer, basestring):
                return pointer
            return pointer.node_name

    def index(self, row, column, parent):
        if not parent.isValid():
            # We have a top level module.
            try:
                module = self._top_level_modules[row]
            except IndexError:
                return QtCore.QModelIndex()
            return self.createIndex(row, column, module)

        parent_pointer = parent.internalPointer()
        if isinstance(parent_pointer, basestring):
            children = self._joints_child_modules[parent_pointer]
        elif parent_pointer:
            children = self._modules_child_joints[parent_pointer]

        try:
            pointer = children[row]
        except IndexError:
            return QtCore.QModelIndex()

        return self.createIndex(row, column, pointer)

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        pointer = index.internalPointer()
        if isinstance(pointer, basestring):
            # We got a joint, so the parent pointer
            # will be a module.
            # We must find the module 
            parent_pointer = self._joints_parent_module[pointer]
        elif pointer:
            parent_pointer = self._modules_parent_joint[pointer]
            if not parent_pointer:
                # We hit a top-level module.
                return QtCore.QModelIndex()

        if isinstance(parent_pointer, basestring):
            great_parent_pointer = self._joints_parent_module[parent_pointer]
            great_children = self._modules_child_joints[great_parent_pointer]
        elif parent_pointer:
            great_parent_pointer = self._modules_parent_joint[parent_pointer]
            if not great_parent_pointer:
                # We hit a top-level module.
                row = self._top_level_modules.index(parent_pointer)
                return self.createIndex(row, 0, self._top_level_modules[row])
            great_children = self._joints_child_modules[great_parent_pointer]

        row = great_children.index(parent_pointer)
        return self.createIndex(row, 0, parent_pointer)
