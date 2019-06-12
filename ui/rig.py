import maya.cmds as cmds
import json
import random
import pdb
from collections import defaultdict
from weakref import WeakValueDictionary

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

        modules_layout.addWidget(self.tree_view)

        actions_layout.addWidget(refresh_button)
        actions_layout.addWidget(self.build_button)
        actions_layout.addWidget(self.unbuild_button)
        actions_layout.addWidget(self.publish_button)

        self._module_icon = QtGui.QIcon(':QR_settings.png')
        self._joint_icon = QtGui.QIcon(':kinJoint.png')
        self._items = {}
        self._module_items = {}
        self._joint_items = {}
        self._joint_parent_modules = WeakValueDictionary()

        self.model = QtGui.QStandardItemModel()
        self._populate_model(Rig().rig_modules)
        self.tree_view.setModel(self.model)
        self.tree_view.header().hide()
        self.tree_view.expandAll()
        selection_model = self.tree_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_changed)

        self._update_buttons_enabled()

        refresh_button.released.connect(self._refresh_model)
        self.build_button.released.connect(self._on_build_rig)
        self.unbuild_button.released.connect(self._on_unbuild_rig)
        self.publish_button.released.connect(self._on_publish_rig)

        subscribe('modules-created', self._on_modules_created)
        subscribe('modules-updated', self._on_modules_updated)
        subscribe('modules-deleted', self._on_modules_deleted)

    def _is_module_item(self, item):
        # HACK: 'cause you know, nothing's perfect.
        # https://bugreports.qt.io/browse/PYSIDE-74
        return id(item) in (id(x) for x in self._module_items.values())

    def _populate_model(self, modules):
        new_module_items = []
        new_joint_items = []
        for module in modules:
            module_item = self._create_module_item(module)
            new_module_items.append((module, module_item))
            for joint in module.deform_joints:
                joint_item = self._create_joint_item(module, joint)
                new_joint_items.append((joint, joint_item))

        root = self.model.invisibleRootItem()

        for module, item in new_module_items:
            self._auto_parent_module_item(module, item, root)

        for joint, item in new_joint_items:
            self._auto_parent_joint_item(joint, item)

    def _create_module_item(self, module):
        item = QtGui.QStandardItem(module.node_name)
        item.setIcon(self._module_icon)
        item.setEditable(False)
        item.setDropEnabled(False)
        if module.name.get() == 'root':
            item.setDragEnabled(False)
        self._module_items[module] = item
        self._items[item.text()] = module
        return item

    def _create_joint_item(self, module, joint):
        item = QtGui.QStandardItem(joint)
        item.setIcon(self._joint_icon)
        item.setEditable(False)
        item.setDragEnabled(False)
        self._joint_items[joint] = item
        self._joint_parent_modules[joint] = module
        self._items[item.text()] = joint
        return item

    def _auto_parent_module_item(self, module, item, default_parent=None):
        if module.parent_module:
            parent_item = self._module_items[module.parent_module]
        else:
            parent_item = default_parent or self.model.invisibleRootItem()
        index = self._child_index_before_joints(parent_item)
        parent_item.insertRow(index, item)

    def _auto_parent_joint_item(self, joint, item):
        module = self._joint_parent_modules[joint]
        parent_item = self._module_items[module]
        parent_item.appendRow(item)

    def _child_index_before_joints(self, item):
        for row in xrange(item.rowCount()):
            child = item.child(row)
            if not self._is_module_item(child):
                return row
        return 0

    def _on_modules_created(self, modules):
        self._populate_model(modules)

    def _on_modules_updated(self, modules):
        for module in modules:
            module_item = self._module_items[module]

            module_name = module.node_name
            was_renamed = module_item.text() != module_name
            if was_renamed:
                module_item.setText(module_name)

            old_parent = module_item.parent().text()
            current_parent = module.parent_module.node_name
            if old_parent != current_parent:
                search_flags = QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive
                matching_items = self.model.findItems(current_parent, search_flags)
                if not matching_items:
                    raise ValueError(
                        'New parent %s has no item in the GUI.' % current_parent
                    )
                new_parent_item = matching_items[0]
                module_item.parent().takeRow(module_item.row())
                index = self._child_index_before_joints(new_parent_item)
                new_parent_item.insertRow(index, module_item)

            joint_items = [
                module_item.child(row) for row in xrange(module_item.rowCount())
            ]
            joints = module.deform_joints.get()

            if len(joints) > len(joint_items):
                self._fill_missing_joint_items(module, joints, joint_items)
            else:
                self._remove_unused_items(joints, joint_items)

            if was_renamed:
                self._rename_child_joint_items(module_item, joints)

    def _fill_missing_joint_items(self, module, joints, joint_items):
        added_joints = joints[len(joint_items) :]
        for joint in added_joints:
            joint_item = self._create_joint_item(module, joint)
            self._auto_parent_joint_item(joint, joint_item)

    def _remove_unused_items(self, joints, joint_items):
        items_to_remove = joint_items[len(joints) :]
        for joint_item in items_to_remove:
            parent = joint_item.parent()
            row = joint_item.row()
            if joint_item.rowCount() > 0:
                self._reparent_child_items_to_previous_sibling(joint_item)
            parent.removeRow(row)

    def _reparent_child_items_to_previous_sibling(self, item):
        parent = item.parent()
        row = item.row()
        big_brother = parent.child(row - 1)
        for child_row in range(item.rowCount()):
            child_item = item.takeChild(child_row)
            big_brother.appendRow(child_item)

    def _rename_child_joint_items(self, module_item, joint_names):
        joint_items = [module_item.child(row) for row in xrange(module_item.rowCount())]
        for name, joint_item in zip(joint_names, joint_items):
            joint_item.setText(name)

    def _on_modules_deleted(self, modules):
        for module in modules:
            item = self._module_items[module]
            parent_item = item.parent()
            if not parent_item:
                continue
            row = item.row()
            parent_item.removeRow(row)

    def _refresh_model(self, modules=None):
        # TODO: update buttons state
        pass

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
        items = [self.model.itemFromIndex(index) for index in selected]
        joints = [
            self._items[item.text()] for item in items if not self._is_module_item(item)
        ]
        modules = [
            self._items[item.text()] for item in items if self._is_module_item(item)
        ]
        if joints:
            cmds.select(joints)
        publish('selected-modules-changed', modules)


class ModulesTree(QtWidgets.QTreeView):
    """A tree view for modules and their deform joints.

    You can drag and drop a module on a joint to parent it.
    """

    def __init__(self, parent=None):
        super(ModulesTree, self).__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

