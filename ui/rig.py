import maya.cmds as cmds
import json
import random
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

        self._module_icon = QtGui.QIcon(':QR_settings.png')
        self._item_modules = {}
        self._module_items = {}

        self.model = ModulesModel()
        self._populate_model(Rig().rig_modules)
        self.tree_view.setModel(self.model)
        self.tree_view.header().hide()
        self.tree_view.expandAll()
        selection_model = self.tree_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_changed)
        if self.model.is_colored:
            random_colors.setChecked(True)

        self._update_buttons_enabled()

        random_colors.toggled.connect(self._on_random_colors_toggled)
        refresh_button.released.connect(self._refresh_model)
        self.build_button.released.connect(self._on_build_rig)
        self.unbuild_button.released.connect(self._on_unbuild_rig)
        self.publish_button.released.connect(self._on_publish_rig)

        subscribe('modules-created', self._on_modules_created)
        subscribe('modules-updated', self._on_modules_updated)
        subscribe('modules-deleted', self._on_modules_deleted)

    def _populate_model(self, modules):
        new_module_items = []
        for module in modules:
            module_item = self._create_module_item(module)
            new_module_items.append((module, module_item))

        root = self.model.invisibleRootItem()

        for module, item in new_module_items:
            self._auto_parent_module_item(module, item, root)

    def _create_module_item(self, module):
        item = QtGui.QStandardItem(module.node_name)
        item.setIcon(self._module_icon)
        item.setEditable(False)
        item.setDropEnabled(True)
        if module.name.get() == 'root':
            item.setDragEnabled(False)
        self._module_items[module] = item
        self._item_modules[item.text()] = module
        return item

    def _auto_parent_module_item(self, module, item, default_parent=None):
        if module.parent_module:
            parent_item = self._module_items[module.parent_module]
        else:
            parent_item = default_parent or self.model.invisibleRootItem()
        parent_item.appendRow(item)

    def _on_modules_created(self, modules):
        self._populate_model(modules)

    def _on_modules_updated(self, modules):
        for module in modules:
            module_item = self._module_items[module]

            module_name = module.node_name
            was_renamed = module_item.text() != module_name
            if was_renamed:
                del self._item_modules[module_item.text()]
                self._item_modules[module_name] = module
                module_item.setText(module_name)

    def _on_modules_deleted(self, modules):
        for module in modules:
            item = self._module_items.pop(module)
            del self._item_modules[item.text()]
            parent_item = item.parent()
            if not parent_item:
                continue
            row = item.row()
            parent_item.removeRow(row)

    def _refresh_model(self, modules=None):
        # TODO: update buttons state
        pass

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
        items = [self.model.itemFromIndex(index) for index in selected]
        modules = [self._item_modules[item.text()] for item in items]
        publish('selected-modules-changed', modules)


class ModulesTree(QtWidgets.QTreeView):
    """A tree view for modules.

    You can drag and drop a module on another one to parent it.
    """

    def __init__(self, parent=None):
        super(ModulesTree, self).__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )


class ModulesModel(QtGui.QStandardItemModel):
    """A model storing modules.

    In this model, modules are stored as :class:`mop.core.module.RigModule`.
    """

    def __init__(self, parent=None):
        super(ModulesModel, self).__init__(parent)
        self._random_colors = False

        settings = get_settings()
        random_colors = bool(int(settings.value('modules/random_colors') or 0))
        if random_colors:
            self.random_colors_on()

    @property
    def is_colored(self):
        """Return ``True`` if this model is randomly colored.

        :rtype: bool
        """
        return self._random_colors

    def random_colors_on(self):
        self._random_colors = True
        settings = get_settings()
        settings.setValue('modules/random_colors', 1)

    def random_colors_off(self):
        self._random_colors = False
        settings = get_settings()
        settings.setValue('modules/random_colors', 0)

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeTypes(self):
        types = super(ModulesModel, self).mimeTypes()
        types.append('application/text')
        return types

    def mimeData(self, indices):
        data = super(ModulesModel, self).mimeData(indices) or QtCore.QMimeData()
        names = []
        for index in indices:
            if not index.isValid():
                continue
            names.append(self.data(index, QtCore.Qt.DisplayRole))
        data.setData('application/text', json.dumps(names))
        return data

    def canDropMimeData(self, data, action, row, column, parent):
        res = super(ModulesModel, self).canDropMimeData(data, action, row, column, parent)
        if not res:
            return False
        if Rig().is_built.get():
            return False
        if not data.hasFormat('application/text'):
            return False
        if not parent.isValid():
            return False
        return True

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        if action == QtCore.Qt.IgnoreAction:
            return True

        rig = Rig()

        names = json.loads(data.data('application/text').data())
        module_name = self.data(parent, QtCore.Qt.DisplayRole)
        parent_module = rig.get_module(module_name)
        modules = []
        for name in names:
            module = rig.get_module(name)
            module.parent_module = parent_module
            module.update()
            modules.append(module)

        publish('modules-updated', modules)

        return super(ModulesModel, self).dropMimeData(data, action, row, column, parent)
