from icarus.core.module import RigModule

class Chain(RigModule):
    def __init__(self, *args, **kwargs):
        super(Chain, self).__init__(*args, **kwargs)
        print "Creating Chain Module"

exported_rig_modules = [Chain]
