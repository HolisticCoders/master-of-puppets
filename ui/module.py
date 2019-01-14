from operator import attrgetter
from weakref import WeakValueDictionary

from icarus.vendor.Qt import QtCore, QtWidgets
from icarus.ui.signals import publish, subscribe, unsubscribe
from icarus.ui.utils import clear_layout
from icarus.ui.fieldwidgets import map_field_to_widget
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class ModulePanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ModulePanel, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName('icarus_settings_panel')
        self._module_widgets = WeakValueDictionary()

        self.setWindowTitle('Icarus Module Panel')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.form = QtWidgets.QFormLayout()
        self.apply_button = QtWidgets.QPushButton('Apply')

        layout.addLayout(self.form)
        layout.addWidget(self.apply_button)

        self.apply_button.released.connect(self._update_module)
        self.apply_button.hide()

        subscribe('selected-module-changed', self._on_module_selected)

    def _on_module_selected(self, module):
        """Update the module to edit."""
        self.module = module
        self._update_ui()

    def _update_module(self):
        """Update the Maya module."""
        if not self.module:
            return
        for name, widget in self._module_widgets.iteritems():
            field = getattr(self.module, name)
            value = widget.get()
            field.set(value)
        self.module.update()
        publish('module-updated')

    def _update_ui(self):
        clear_layout(self.form)
        if not self.module:
            self.apply_button.hide()
            return
        if self.module.is_built.get():
            self.apply_button.setEnabled(False)
        else:
            self.apply_button.setEnabled(True)
        self.apply_button.show()
        ordered_fields = sorted(
            self.module.fields,
            key=attrgetter('gui_order')
        )
        for field in ordered_fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name,
                map_field_to_widget['StringField']
            )
            widget = widget_data(field)
            value = getattr(self.module, field.name).get()
            widget.set(value)

            self._module_widgets[field.name] = widget

            self.form.addRow(field.display_name, widget)

            if not field.editable or self.module.is_built.get():
                widget.setEnabled(False)

    def close(self):
        unsubscribe('selected-module-changed', self._on_module_selected)
        return super(ModulePanel, self).close()
