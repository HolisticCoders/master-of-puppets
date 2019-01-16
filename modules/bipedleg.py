from icarus.modules.fkikrpchain import FkIkRPChain


class BipedLeg(FkIkRPChain):
    def initialize(self):
        super(BipedLeg, self).initialize()
        self.ik_start_description.set('IK_ankle')
        self.ik_end_description.set('IK_hip')


exported_rig_modules = [BipedLeg]
