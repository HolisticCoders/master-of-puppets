import maya.cmds as cmds
import json
import random
import pdb
from collections import defaultdict
from weakref import WeakKeyDictionary, WeakSet

from mop.vendor.Qt import QtCore, QtGui, QtWidgets
from mop.core.rig import Rig
from mop.ui.settings import get_settings
from mop.ui.signals import publish, subscribe
from mop.ui.commands import build_rig, unbuild_rig, publish_rig
from mop.ui.utils import hsv_to_rgb


class RigPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RigPanel, self).__init__(parent)
        self.setObjectName('mop_rig_panel')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Rig Panel')

        self.modules_group = QtWidgets.QGroupBox('Modules')
        self.actions_group = QtWidgets.QGroupBox('Actions')

        random_colors = QtWidgets.QCheckBox('Random Colors')
        self.tree_view = ModulesTree()
        refresh_button = QtWidgets.QPushButton('Refresh')
        self.build_button = QtWidgets.QPushButton('Build Rig')
        self.unbuild_button = QtWidgets.QPushButton('Unbuild Rig')
        self.publish_button = QtWidgets.QPushButton('Publish Rig')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.modules_group)
        layout.addWidget(self.actions_group)

        modules_layout = QtWidgets.QVBoxLayout()
        options_layout = QtWidgets.QHBoxLayout()
        actions_layout = QtWidgets.QHBoxLayout()

        self.modules_group.setLayout(modules_layout)
        self.actions_group.setLayout(actions_layout)

        modules_layout.addLayout(options_layout)
        options_layout.addWidget(random_colors)

        modules_layout.addWidget(self.tree_view)

        actions_layout.addWidget(refresh_button)
        actions_layout.addWidget(self.build_button)
        actions_layout.addWidget(self.unbuild_button)
        actions_layout.addWidget(self.publish_button)

        self._refresh_model()
        if self.model.is_colored:
            random_colors.setChecked(True)

        self._update_buttons_enabled()

        random_colors.toggled.connect(self._on_random_colors_toggled)
        refresh_button.released.connect(self._refresh_model)
        self.build_button.released.connect(self._on_build_rig)
        self.unbuild_button.released.connect(self._on_unbuild_rig)
        self.publish_button.released.connect(self._on_publish_rig)

        subscribe('modules-created', self._refresh_model)
        subscribe('modules-updated', self._refresh_model)
        subscribe('modules-deleted', self._refresh_model)

    def _refresh_model(self, modules=None):
        self.model = ModulesModel()
        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        selection_model = self.tree_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_changed)

        # Restore selection.
        # NOTE: maybe optimize this part, and keep the same
        # model for the whole session, instead of discarding
        # it for any module added/deleted/changed.
        indices = []
        if modules:
            # Filter in case we stumble upon deleted module.
            # In this case, they won't have any index in the tree.
            indices = filter(None, map(self._find_index, modules))
            selection = QtCore.QItemSelection()
            selection_model.clear()
            for index in indices:
                selection.select(index, index)
            selection_model.select(
                selection,
                QtCore.QItemSelectionModel.Select,
            )
            selection_model.setCurrentIndex(
                indices[-1],
                QtCore.QItemSelectionModel.Current,
            )

    def _find_index(self, module, index=QtCore.QModelIndex()):
        """Return a Qt index to ``module``.

        If there is no modules model yet, or the module cannot be
        found, return ``None``.

        A matching index is an index containing a module of the same
        :attr:`mop.core.module.RigModule.node_name` as the passed
        module.

        :param module: Module to find the index of.
        :param index: Parent index of the search, since we are in a
                      tree view.
        :type module: mop.core.module.RigModule
        :type index: PySide2.QtCore.QModelIndex
        :rtype: PySide2.QtCore.QModelIndex
        """
        if not self.model:
            return None
        name = module.node_name
        for i in xrange(self.model.rowCount(index)):
            child = self.model.index(i, 0, index)
            pointer = child.internalPointer()
            if not isinstance(pointer, basestring):
                if pointer.node_name == name:
                    return child
            _index = self._find_index(module, child)
            if _index:
                return _index

    def _on_random_colors_toggled(self, checked):
        if not self.model:
            return
        if checked:
            self.model.random_colors_on()
        else:
            self.model.random_colors_off()

    def _on_build_rig(self):
        build_rig()
        self._update_buttons_enabled()

    def _on_unbuild_rig(self):
        unbuild_rig()
        self._update_buttons_enabled()

    def _on_publish_rig(self):
        publish_rig()
        self._update_buttons_enabled()

    def _update_buttons_enabled(self):
        if Rig().is_built.get():
            self.build_button.setEnabled(False)
            self.unbuild_button.setEnabled(True)
            self.publish_button.setEnabled(True)
        else:
            self.build_button.setEnabled(True)
            self.unbuild_button.setEnabled(False)
            self.publish_button.setEnabled(False)

    def _on_selection_changed(self, selected, deselected):
        selection = self.tree_view.selectionModel()
        selected = selection.selectedRows()
        pointer = [index.internalPointer() for index in selected]
        joints = [p for p in pointer if isinstance(p, basestring)]
        cmds.select(joints)
        publish('selected-modules-changed', pointer)


class ModulesTree(QtWidgets.QTreeView):
    """A tree view for modules and their deform joints.

    You can drag and drop a module on a joint to parent it.
    """

    def __init__(self, parent=None):
        super(ModulesTree, self).__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )


class ModulesModel(QtCore.QAbstractItemModel):
    """A model storing modules and their deform joints.

    In this model, joints are stored as :class:`str` instances,
    and modules as :class:`mop.core.module.RigModule`.
    """

    def __init__(self, parent=None):
        super(ModulesModel, self).__init__(parent)
        self._random_colors = False
        self.invalidate_cache()

        settings = get_settings()
        random_colors = bool(int(settings.value('modules/random_colors') or 0))
        if random_colors:
            self.random_colors_on()

    def invalidate_cache(self):
        """Refresh the cache."""
        rig = Rig()
        self.modules = rig.rig_modules

        self._module_colors = {}
        self._top_level_modules = []
        self._joints_parent_module = {}
        self._joints_child_modules = defaultdict(list)
        self._modules_parent_joint = {}
        self._modules_child_joints = defaultdict(list)

        for module in self.modules:
            self._module_colors[module] = random.random()
            parent = module.parent_joint.get()
            self._modules_parent_joint[module] = parent
            self._joints_child_modules[parent].append(module)
            if parent is None:
                self._top_level_modules.append(module)
            for joint in module.deform_joints:
                self._joints_parent_module[joint] = module
                self._modules_child_joints[module].append(joint)

    @property
    def is_colored(self):
        """Return ``True`` if this model is randomly colored.

        :rtype: bool
        """
        return self._random_colors

    def random_colors_on(self):
        self._random_colors = True
        parent = QtCore.QModelIndex()
        self.dataChanged.emit(
            self.index(0, 0, parent),
            self.index(self.rowCount(parent), 0, parent),
            [QtCore.Qt.ForegroundRole],
        )

        settings = get_settings()
        settings.setValue('modules/random_colors', 1)

    def random_colors_off(self):
        self._random_colors = False
        parent = QtCore.QModelIndex()
        self.dataChanged.emit(
            self.index(0, 0, parent),
            self.index(self.rowCount(parent), 0, parent),
            [QtCore.Qt.ForegroundRole],
        )

        settings = get_settings()
        settings.setValue('modules/random_colors', 0)

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
        elif role == QtCore.Qt.DecorationRole:
            if isinstance(pointer, basestring):
                return QtGui.QIcon(':kinJoint.png')
            return QtGui.QIcon(':QR_settings.png')
        elif role == QtCore.Qt.ForegroundRole:
            if not self._random_colors:
                return
            if isinstance(pointer, basestring):
                module = index.parent().internalPointer()
            else:
                module = index.internalPointer()
            color = hsv_to_rgb(self._module_colors[module], .3, .80)
            return QtGui.QBrush(QtGui.QColor(*color))

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

    def flags(self, index):
        default_flags = super(ModulesModel, self).flags(index)
        if Rig().is_built.get():
            if not isinstance(index.internalPointer(), basestring):
                return default_flags
            return QtCore.Qt.ItemIsEnabled

        if not index.isValid():
            return default_flags

        if not isinstance(index.internalPointer(), basestring):
            # Only allow modules to be dragged.
            return (QtCore.Qt.ItemIsDragEnabled
                    | QtCore.Qt.ItemIsDropEnabled
                    | default_flags)

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsSelectable

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['application/text']

    def mimeData(self, indices):
        data = QtCore.QMimeData()
        names = []
        for index in indices:
            if not index.isValid():
                continue
            names.append(self.data(index, QtCore.Qt.DisplayRole))
        data.setData('application/text', json.dumps(names))
        return data

    def canDropMimeData(self, data, action, row, column, parent):
        if Rig().is_built.get():
            return False
        if not data.hasFormat('application/text'):
            return False
        if column > 0:
            return False
        if not parent.isValid():
            return False
        if not isinstance(parent.internalPointer(), basestring):
            # Only allow modules to be dropped on joints.
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        if action == QtCore.Qt.IgnoreAction:
            return True

        names = json.loads(data.data('application/text').data())

        parent_pointer = None
        if parent.isValid():
            parent_pointer = parent.internalPointer()

        drop_row = 0
        if row != -1:
            drop_row = row
        elif parent.isValid():
            drop_row = parent.row()
        else:
            drop_row = self.rowCount(QtCore.QModelIndex())

        if parent_pointer and not isinstance(parent_pointer, basestring):
            # We hit a parent module, selected module has been dropped
            # after the deform joint and not on it, so select the deform
            # joint just before `drop_row`.
            joint_index = self.index(drop_row - 1, column, parent)
        else:
            joint_index = parent

        joint = None
        if joint_index.isValid():
            joint = joint_index.internalPointer()

        rig = Rig()
        modules = []
        for name in names:
            module = rig.get_module(name)
            module.parent_joint.set(joint)
            module.update()
            modules.append(module)

        publish('modules-updated', modules)

        return True
