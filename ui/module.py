from functools import partial
from operator import attrgetter
from weakref import WeakValueDictionary

from icarus.vendor.Qt import QtCore, QtWidgets
from icarus.core.rig import Rig
from icarus.ui.signals import publish, subscribe, unsubscribe
from icarus.ui.utils import clear_layout
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class ISpinBox(QtWidgets.QSpinBox):
    def __init__(self, field, *args, **kwargs):
        super(ISpinBox, self).__init__(*args, **kwargs)
        self.field = field
        minValue = field.min_value
        maxValue = field.max_value
        if minValue is not None:
            self.setMinimum(minValue)
        else:
            self.setMinimum(-1000000)
        if maxValue is not None:
            self.setMaximum(maxValue)
        else:
            self.setMaximum(1000000)

    def get(self):
        return self.value()

    def set(self, value):
        self.setValue(value)

    def signal(self):
        return self.valueChanged


class ILineEdit(QtWidgets.QLineEdit):
    def __init__(self, field, *args, **kwargs):
        super(ILineEdit, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setText(value)

    def get(self):
        return self.text()

    def signal(self):
        return self.textChanged


class ICheckBox(QtWidgets.QCheckBox):
    def __init__(self, field, *args, **kwargs):
        super(ICheckBox, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setChecked(value)

    def get(self):
        return self.isChecked()

    def signal(self):
        return self.stateChanged


map_field_to_widget = {
    'BoolField': ICheckBox,
    'IntField': ISpinBox,
    'StringField': ILineEdit,
    'ObjectField': ILineEdit,
}


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
        ordered_fields = sorted(self.module.fields, key=attrgetter('gui_order'))
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
