from functools import partial

from icarus.vendor.Qt import QtWidgets
from icarus.modules.chain import Chain
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

map_field_to_widget = {
    'BoolField': {
        'widget': QtWidgets.QCheckBox,
        'setter': 'setChecked',
        'getter': 'isChecked',
    },
    'IntField': {
        'widget': QtWidgets.QSpinBox,
        'setter': 'setValue',
        'getter': 'value',
        'signal': 'valueChanged',
    },
    'StringField': {
        'widget': QtWidgets.QLineEdit,
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

            widget = widget_data['widget']()
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
