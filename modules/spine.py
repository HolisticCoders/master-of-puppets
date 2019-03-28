from mop.core.fields import IntField
from mop.modules.chain import Chain


class Spine(Chain):

    joint_count = IntField(
        defaultValue=3,
        hasMinValue=True,
        minValue=3,
        hasMaxValue=True,
        maxValue=3
    )


exported_rig_modules = [Spine]
