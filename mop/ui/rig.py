from math import floor

import maya.cmds as cmds

from mop.config.default_config import side_color
from mop.core.rig import Rig
from mop.ui.commands import build_rig, unbuild_rig, publish_rig
from mop.ui.settings import get_settings
from mop.ui.signals import publish, subscribe
from mop.utils.colorspace import linear_to_srgb
from mop.vendor.Qt import QtCore, QtGui, QtWidgets


class RigPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RigPanel, self).__init__(parent)
        self.setObjectName("mop_rig_panel")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Rig Panel")

        self.modules_group = QtWidgets.QGroupBox("Modules")
        self.actions_group = QtWidgets.QGroupBox("Actions")

        color_by_side = QtWidgets.QCheckBox("Colors by Side")

        self.joints_mode_group = QtWidgets.QButtonGroup()
        self.joints_mode_label = QtWidgets.QLabel("Display Children:")
        self.joints_mode_none = QtWidgets.QRadioButton("None")
        self.joints_mode_deform = QtWidgets.QRadioButton("Deform Joints")
        self.joints_mode_control = QtWidgets.QRadioButton()
        self._update_display_names()

        self.search_label = QtWidgets.QLabel("Search")
        self.search_bar = QtWidgets.QLineEdit()

        self.tree_view = ModulesTree()
        self.build_button = QtWidgets.QPushButton("Build Rig")
        self.unbuild_button = QtWidgets.QPushButton("Unbuild Rig")
        self.publish_button = QtWidgets.QPushButton("Publish Rig")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.modules_group)
        layout.addWidget(self.actions_group)

        modules_layout = QtWidgets.QVBoxLayout()
        options_layout = QtWidgets.QHBoxLayout()
        search_layout = QtWidgets.QHBoxLayout()
        actions_layout = QtWidgets.QHBoxLayout()

        self.modules_group.setLayout(modules_layout)
        self.actions_group.setLayout(actions_layout)

        modules_layout.addLayout(options_layout)
        options_layout.addWidget(color_by_side)

        options_layout.addStretch()

        options_layout.addWidget(self.joints_mode_label)
        options_layout.addWidget(self.joints_mode_none)
        options_layout.addWidget(self.joints_mode_deform)
        options_layout.addWidget(self.joints_mode_control)

        modules_layout.addLayout(search_layout)
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_bar)

        modules_layout.addWidget(self.tree_view)

        actions_layout.addWidget(self.build_button)
        actions_layout.addWidget(self.unbuild_button)
        actions_layout.addWidget(self.publish_button)

        # Icons
        self._module_icon = QtGui.QIcon(":QR_settings.png")
        self._joint_icon = QtGui.QIcon(":kinJoint.png")
        self._control_icon = QtGui.QIcon(":nurbsCurve.svg")

        # GUI colors
        raw_left = side_color["L"]
        raw_right = side_color["R"]
        raw_middle = side_color["M"]
        srgb_left = map(linear_to_srgb, raw_left)
        srgb_right = map(linear_to_srgb, raw_right)
        srgb_middle = map(linear_to_srgb, raw_middle)
        left_color = self._float_to_256_color(srgb_left)
        right_color = self._float_to_256_color(srgb_right)
        middle_color = self._float_to_256_color(srgb_middle)
        self._left_brush = QtGui.QBrush(QtGui.QColor(*left_color))
        self._right_brush = QtGui.QBrush(QtGui.QColor(*right_color))
        self._middle_brush = QtGui.QBrush(QtGui.QColor(*middle_color))
        self._colors = {
            "L": self._left_brush,
            "R": self._right_brush,
            "M": self._middle_brush,
            "base": QtGui.QBrush(QtGui.QColor(187, 187, 187)),
        }

        settings = get_settings()
        self._color_by_side = bool(int(settings.value("modules/color_by_side") or 0))

        if self._color_by_side:
            color_by_side.setChecked(True)

        display_mode = settings.value("modules/joints_display_mode")
        if display_mode is None:
            display_mode = 1
        else:
            display_mode = int(display_mode)

        if display_mode == 0:
            self.joints_mode_none.setChecked(True)
        elif display_mode == 1:
            self.joints_mode_deform.setChecked(True)
        elif display_mode == 2:
            self.joints_mode_control.setChecked(True)

        self.tree_view.header().hide()
        self._generate_model()

        self._update_buttons_enabled()

        self.joints_mode_group.addButton(self.joints_mode_none)
        self.joints_mode_group.addButton(self.joints_mode_deform)
        self.joints_mode_group.addButton(self.joints_mode_control)

        color_by_side.toggled.connect(self._on_color_by_side_toggled)
        self.joints_mode_group.buttonClicked.connect(self._on_joints_mode_clicked)
        self.search_bar.textEdited.connect(self._on_search_changed)
        self.build_button.released.connect(self._on_build_rig)
        self.unbuild_button.released.connect(self._on_unbuild_rig)
        self.publish_button.released.connect(self._on_publish_rig)

        self._refresh_script_job_ids = self._setup_refresh_script_job()

        subscribe("modules-created", self._on_modules_created)
        subscribe("modules-updated", self._on_modules_updated)
        subscribe("modules-deleted", self._on_modules_deleted)

    def showEvent(self, event):
        self.tree_view.setFocus(QtCore.Qt.ActiveWindowFocusReason)

    def closeEvent(self, event):
        for event, script_job_id in self._refresh_script_job_ids:
            try:
                cmds.scriptJob(kill=script_job_id)
            except RuntimeError:
                logger.warning("Refresh script job for %s was already deleted.", event)

    @property
    def _display_mode(self):
        settings = get_settings()
        display_mode = settings.value("modules/joints_display_mode")
        if display_mode is None:
            return 1
        else:
            return int(display_mode)

    def _generate_model(self):
        selection_model = self.tree_view.selectionModel()
        if selection_model:
            selection_model.selectionChanged.disconnect(self._on_selection_changed)

        self.model = ModulesModel()
        self.proxy = ModulesFilter()
        self.proxy.setSourceModel(self.model)
        self.proxy.setDisplayMode(self._display_mode)

        self._populate_model(Rig().rig_modules, expand_new_modules=False)

        self.tree_view.setModel(self.proxy)
        self.tree_view.expandAll()

        selection_model = self.tree_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_changed)

    def _on_color_by_side_toggled(self, checked):
        self._color_by_side = checked
        settings = get_settings()
        settings.setValue("modules/color_by_side", 1 if checked else 0)

        if not self.model:
            return

        root = self.model.invisibleRootItem()
        if checked:
            self._show_colors_recursively(root)
        else:
            self._hide_colors_recursively(root)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def _on_joints_mode_clicked(self, button):
        if button == self.joints_mode_deform:
            self.proxy.setDisplayMode(1)
        elif button == self.joints_mode_control:
            self.proxy.setDisplayMode(2)
        else:
            self.proxy.setDisplayMode(0)

    def _on_search_changed(self, search):
        self.proxy.setFilterRegExp(search)

    def _iter_items_recursively(self, parent):
        for row in xrange(parent.rowCount()):
            item = parent.child(row)
            yield item
            for child in self._iter_items_recursively(item):
                yield child

    def _show_colors_recursively(self, parent):
        for item in self._iter_items_recursively(parent):
            if self.model.is_module_item(item):
                module = Rig().get_module(item.text())
            else:
                module = self._joint_parent_module(item.text())
            item.setForeground(self._colors[module.side.get()])

    def _hide_colors_recursively(self, parent):
        for item in self._iter_items_recursively(parent):
            item.setForeground(self._colors["base"])

    def _float_to_256_color(self, color):
        def _float_to_256(value):
            return int(floor(255 if value >= 1.0 else value * 256))

        return map(_float_to_256, color)

    def _item_for_name(self, name):
        search_flags = QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive
        matching_items = self.model.findItems(name, search_flags)
        if not matching_items:
            raise ValueError('No item with text "%s" found' % name)
        return matching_items[0]

    def _joint_parent_module(self, joint):
        modules = cmds.listConnections(joint + ".module", source=True)
        if not modules:
            raise AttributeError("Joint %s is not connected to a module !" % joint)
        module = modules[0]
        return Rig().get_module(module)

    def _setup_refresh_script_job(self):
        ids = []
        for event in ("Undo", "Redo"):
            script_job_id = cmds.scriptJob(
                event=(event, self._update_ui_state), parent="mop_rig_panel"
            )
            ids.append((event, script_job_id))
        return ids

    def _populate_model(self, modules, expand_new_modules=True):
        new_module_items = []
        new_joint_items = []
        for module in modules:
            module_item = self._create_module_item(module)
            new_module_items.append((module, module_item))
            for joint in module.deform_joints:
                joint_item = self._create_joint_item(module, joint)
                new_joint_items.append((joint, joint_item))
            if not Rig().is_built.get():
                for guide in module.guide_nodes:
                    guide_item = self._create_control_item(module, guide)
                    new_joint_items.append((guide, guide_item))
            else:
                for control in module.controllers:
                    control_item = self._create_control_item(module, control)
                    new_joint_items.append((control, control_item))

        root = self.model.invisibleRootItem()

        for module, item in new_module_items:
            self._auto_parent_module_item(module, item, root)
            if expand_new_modules:
                source_index = self.model.indexFromItem(item)
                index = self.proxy.mapFromSource(source_index)
                self.tree_view.setExpanded(index, True)

        for joint, item in new_joint_items:
            self._auto_parent_joint_item(joint, item)

    def _create_module_item(self, module):
        item = self._create_item(module, module.node_name)
        item.setIcon(self._module_icon)
        return item

    def _create_joint_item(self, module, joint):
        item = self._create_item(module, joint)
        item.setIcon(self._joint_icon)
        return item

    def _create_control_item(self, module, control):
        item = self._create_item(module, control)
        item.setIcon(self._control_icon)
        return item

    def _create_item(self, module, name):
        item = QtGui.QStandardItem(name)
        item.setEditable(False)
        if self._color_by_side:
            item.setForeground(self._colors[module.side.get()])
        return item

    def _auto_parent_module_item(self, module, item, default_parent=None):
        if module.parent_module:
            parent_item = self._item_for_name(module.parent_module.node_name)
        else:
            parent_item = default_parent or self.model.invisibleRootItem()
        parent_item.appendRow(item)

    def _auto_parent_joint_item(self, joint, item):
        module = self._joint_parent_module(joint)
        parent_item = self._item_for_name(module.node_name)
        index = self._child_index_before_modules(parent_item)
        parent_item.insertRow(index, [item])

    def _child_index_before_modules(self, item):
        for row in xrange(item.rowCount()):
            child = item.child(row)
            if self.model.is_module_item(child):
                return row
        return item.rowCount()

    def _on_modules_created(self, modules):
        self._populate_model(modules)

    def _on_modules_updated(self, modified_fields):
        selected_items, current_item = self._save_selection()
        expanded_modules = self._save_expanded_modules()
        parents_have_changed = False
        sides_have_changed = False
        for module, modified_values in modified_fields.iteritems():
            if "node_name" in modified_values:
                was_renamed = True
                module_item_name = modified_values["node_name"][0]
                module_item = self._item_for_name(module_item_name)
                module_item.setText(module.node_name)
            else:
                was_renamed = False
                module_item = self._item_for_name(module.node_name)

            if "parent_joint" in modified_values:
                parent_has_changed = True
                self._handle_reparenting(module, module_item)
            else:
                parent_has_changed = False

            parents_have_changed = parents_have_changed or parent_has_changed

            joints = module.deform_joints.get()

            if "joint_count" in modified_values:
                old_joint_count = modified_values["joint_count"][0]
                new_joint_count = modified_values["joint_count"][1]
                joint_items = [
                    module_item.child(row)
                    for row in xrange(module_item.rowCount())
                    if self.model.is_joint_item(module_item.child(row))
                ]
                if new_joint_count > old_joint_count:
                    self._fill_missing_joint_items(module, joints, joint_items)
                    if Rig().is_built.get():
                        controls = module.controllers.get()
                        control_items = [
                            module_item.child(row)
                            for row in xrange(module_item.rowCount())
                            if self.model.is_control_item(module_item.child(row))
                        ]
                    else:
                        controls = module.guide_nodes.get()
                        control_items = [
                            module_item.child(row)
                            for row in xrange(module_item.rowCount())
                            if self.model.is_guide_item(module_item.child(row))
                        ]
                    self._fill_missing_control_items(module, controls, control_items)
                else:
                    self._remove_unused_items(module_item)

            if was_renamed:
                self._rename_child_joint_items(module_item, joints)

            if "side" in modified_values:
                side_has_changed = True
            else:
                side_has_changed = False

            sides_have_changed = sides_have_changed or side_has_changed

        if parents_have_changed:
            self._restore_selection(selected_items, current_item)

        if sides_have_changed and self._color_by_side:
            self._show_colors_recursively(self.model.invisibleRootItem())

        if expanded_modules:
            self._restore_expanded_modules(expanded_modules)

    def _handle_reparenting(self, module, module_item):
        old_parent = module_item.parent().text()
        current_parent = module.parent_module.node_name
        if old_parent == current_parent:
            return False

        try:
            new_parent_item = self._item_for_name(current_parent)
        except ValueError:
            raise ValueError("New parent %s has no item in the GUI." % current_parent)

        child_items = module_item.parent().takeRow(module_item.row())
        module_item = child_items[0]
        new_parent_item.appendRow(module_item)

        return True

    def _save_expanded_modules(self):
        modules = []
        if not self.model:
            return modules

        for item in self._iter_items_recursively(self.model.invisibleRootItem()):
            if not self.model.is_module_item(item):
                continue
            source_index = self.model.indexFromItem(item)
            index = self.proxy.mapFromSource(source_index)
            if self.tree_view.isExpanded(index):
                module = Rig().get_module(item.text())
                modules.append(module)

        return modules

    def _restore_expanded_modules(self, modules):
        if not self.model:
            return
        for module in modules:
            item = self._item_for_name(module.node_name)
            source_index = self.model.indexFromItem(item)
            index = self.proxy.mapFromSource(source_index)
            self.tree_view.setExpanded(index, True)

    def _save_selection(self):
        selection_model = self.tree_view.selectionModel()
        selection = selection_model.selectedRows()
        source_indices = map(self.proxy.mapToSource, selection)
        selected_items = map(self.model.itemFromIndex, source_indices)
        current_index = selection_model.currentIndex()
        current_item = self.model.itemFromIndex(self.proxy.mapToSource(current_index))
        return selected_items, current_item

    def _restore_selection(self, selected_items, current_item):
        selection_model = self.tree_view.selectionModel()
        selection_model.clear()
        for item in selected_items:
            source_index = self.model.indexFromItem(item)
            index = self.proxy.mapFromSource(source_index)
            selection_model.select(index, QtCore.QItemSelectionModel.Select)
        source_current_index = self.model.indexFromItem(current_item)
        current_index = self.proxy.mapFromSource(source_current_index)
        selection_model.setCurrentIndex(
            current_index, QtCore.QItemSelectionModel.Current
        )

    def _fill_missing_joint_items(self, module, joints, joint_items):
        added_joints = joints[len(joint_items) :]
        for joint in added_joints:
            joint_item = self._create_joint_item(module, joint)
            self._auto_parent_joint_item(joint, joint_item)

    def _fill_missing_control_items(self, module, controls, control_items):
        added_controls = controls[len(control_items) :]
        for control in added_controls:
            control_item = self._create_control_item(module, control)
            self._auto_parent_joint_item(control, control_item)

    def _remove_unused_items(self, parent_item):
        for row in reversed(xrange(parent_item.rowCount())):
            child = parent_item.child(row)
            if not cmds.objExists(child.text()):
                parent_item.removeRow(row)

    def _rename_child_joint_items(self, module_item, joint_names):
        joint_items = [module_item.child(row) for row in xrange(module_item.rowCount())]
        for name, joint_item in zip(joint_names, joint_items):
            joint_item.setText(name)

    def _on_modules_deleted(self, modules):
        for module in modules:
            item = self._item_for_name(module.node_name)
            parent_item = item.parent()
            if not parent_item:
                continue
            row = item.row()
            parent_item.removeRow(row)

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
        self._generate_model()
        self._update_ui_state()

    def _on_unbuild_rig(self):
        unbuild_rig()
        self._generate_model()
        self._update_ui_state()

    def _on_publish_rig(self):
        publish_rig()
        self._update_buttons_enabled()

    def _update_ui_state(self):
        self._update_buttons_enabled()
        self._update_display_names()

    def _update_buttons_enabled(self):
        rig = Rig()
        if rig.is_published.get():
            self.build_button.setEnabled(False)
            self.unbuild_button.setEnabled(False)
            self.publish_button.setEnabled(False)
            return
        elif rig.is_built.get():
            self.build_button.setEnabled(False)
            self.unbuild_button.setEnabled(True)
            self.publish_button.setEnabled(True)
        else:
            self.build_button.setEnabled(True)
            self.unbuild_button.setEnabled(False)
            self.publish_button.setEnabled(False)

    def _update_display_names(self):
        if Rig().is_built.get():
            self.joints_mode_control.setText("Controls")
        else:
            self.joints_mode_control.setText("Guides")

    def _on_selection_changed(self, selected, deselected):
        selection = self.tree_view.selectionModel()
        selected = selection.selectedRows()
        source_indices = map(self.proxy.mapToSource, selected)
        items = [self.model.itemFromIndex(index) for index in source_indices]
        joints = [item.text() for item in items if not self.model.is_module_item(item)]
        modules = [
            Rig().get_module(item.text())
            for item in items
            if self.model.is_module_item(item)
        ]
        if joints:
            cmds.select(joints)
        publish("selected-modules-changed", modules)


class ModulesTree(QtWidgets.QTreeView):
    """A tree view for modules and their deform joints.

    You can drag and drop a module on a joint to parent it.
    """

    def __init__(self, parent=None):
        super(ModulesTree, self).__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)


class ModulesModel(QtGui.QStandardItemModel):
    @staticmethod
    def is_item_of_type(item, node_type):
        if not cmds.objExists(item.text()):
            return False
        return cmds.objectType(item.text()) == node_type

    @staticmethod
    def is_module_item(item):
        if not item.text().endswith("mod"):
            return False
        return ModulesModel.is_item_of_type(item, "transform")

    @staticmethod
    def is_control_item(item):
        if item.text().endswith("mod"):
            return False
        return ModulesModel.is_item_of_type(item, "transform")

    @staticmethod
    def is_guide_item(item):
        if not item.text().endswith("guide"):
            return False
        return ModulesModel.is_item_of_type(item, "transform")

    @staticmethod
    def is_joint_item(item):
        return ModulesModel.is_item_of_type(item, "joint")


class ModulesFilter(QtCore.QSortFilterProxyModel):
    """A custom filter taking tree children into account.

    Reimplemented in Python from
    https://github.com/pasnox/fresh/blob/master/src/core/pRecursiveSortFilterProxyModel.h
    """

    def __init__(self, recursiveFilter=True, invertedFilter=False, parent=None):
        super(ModulesFilter, self).__init__(parent)
        self._recursiveFilter = recursiveFilter
        self._invertedFilter = invertedFilter
        self._sourceRootIndex = QtCore.QModelIndex()

        self._display_mode = 1

    def setDisplayMode(self, mode):
        self._display_mode = mode
        self.invalidateFilter()

        settings = get_settings()
        settings.setValue("modules/joints_display_mode", mode)

    def displayMode(self):
        return self._display_mode

    def data(self, index, role):
        if self._sourceRootIndex.isValid():
            if index == QtCore.QModelIndex():
                return None
        return super(ModulesFilter, self).data(index, role)

    def mapFromSource(self, sourceIndex):
        if self._sourceRootIndex.isValid():
            if sourceIndex == self._sourceRootIndex:
                return QtCore.QModelIndex()
        return super(ModulesFilter, self).mapFromSource(sourceIndex)

    def mapToSource(self, proxyIndex):
        if self._sourceRootIndex.isValid():
            if proxyIndex == QtCore.QModelIndex():
                return self._sourceRootIndex
        return super(ModulesFilter, self).mapToSource(proxyIndex)

    def setRecursiveFilter(self, recursive):
        self._recursiveFilter = recursive

    def isRecursiveFilter(self):
        return self._recursiveFilter

    def setInvertedFilter(self, inverted):
        self._invertedFilter = inverted

    def isInvertedFilter(self):
        return self._invertedFilter

    def setSourceRootModelIndex(self, index):
        self.beginResetModel()
        self._sourceRootIndex = index
        self.endResetModel()

    def sourceRootIndex(self):
        return self._sourceRootIndex

    def filterAcceptsRowImplementation(self, source_row, source_parent):
        return super(ModulesFilter, self).filterAcceptsRow(source_row, source_parent)

    def filterAcceptsRow(self, source_row, source_parent):
        """Display parent item which at least one child matches.

        :param source_row: Row of the source index to check.
        :param source_parent: Parent of the source index to check.
        :type source_row: int
        :type source_parent: controllers.gui.Qt.QtCore.QModelIndex
        :rtype: bool
        """
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        item = model.itemFromIndex(index)

        if self._display_mode == 0 and not model.is_module_item(item):
            return False
        elif self._display_mode == 1 and model.is_control_item(item):
            return False
        elif self._display_mode == 1 and model.is_guide_item(item):
            return False
        elif self._display_mode == 2 and model.is_joint_item(item):
            return False

        res = super(ModulesFilter, self).filterAcceptsRow(source_row, source_parent)
        # If the item is already valid, do not make any
        # additional checks.
        if res:
            return res

        # Now recursively check all children to see if one matches.
        if model.hasChildren(index):
            for i in xrange(model.rowCount(index)):
                res = res | self.filterAcceptsRow(i, index)
                if res:
                    return res

        return res
