from functools import partial

from icarus.vendor.Qt import QtWidgets
from icarus.modules.chain import Chain
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


class ILineEdit(QtWidgets.QLineEdit):
    def __init__(self, field, *args, **kwargs):
        super(ILineEdit, self).__init__(*args, **kwargs)
        self.field = field


class ICheckBox(QtWidgets.QCheckBox):
    def __init__(self, field, *args, **kwargs):
        super(ICheckBox, self).__init__(*args, **kwargs)
        self.field = field


map_field_to_widget = {
    'BoolField': {
        'widget': ICheckBox,
        'setter': 'setChecked',
        'getter': 'isChecked',
    },
    'IntField': {
        'widget': ISpinBox,
        'setter': 'setValue',
        'getter': 'value',
        'signal': 'valueChanged',
    },
    'StringField': {
        'widget': ILineEdit,
        'setter': 'setText',
        'getter': 'text'
    },
}


class SettingsPanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(SettingsPanel, self).__init__(parent)
        self.setWindowTitle('Icarus Settings')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)


        module = Chain('pelvis_M_mod')

        for field in module.fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name,
                map_field_to_widget['StringField']
            )

            widget = widget_data['widget'](field)
            value = getattr(module, field.name).get()
            getattr(widget, widget_data['setter'])(value)

            if 'signal' in widget_data:
                getattr(widget, widget_data['signal']).connect(
                    partial(self._update_field, field, module)
                )

            form.addRow(field.display_name, widget)

            if not field.editable:
                widget.setEditable(False)

        update_button = QtWidgets.QPushButton('Apply')
        layout.addWidget(update_button)
        update_button.released.connect(self._update)

    def _update(self):
        module = Chain('pelvis_M_mod')
        module.update()

    def _update_field(self, field, module, value):
        getattr(module, field.name).set(value)
