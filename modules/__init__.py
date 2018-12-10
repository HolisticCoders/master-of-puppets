import os
import importlib


all_rig_modules = {}
for mod in os.listdir(os.path.dirname(__file__)):
    if mod.endswith('.pyc'):
        # print "skipping", mod
        continue
    if mod == os.path.basename(__file__):
        # print "skipping", mod
        continue
    mod_name = 'icarus.modules.' + mod.split('.')[0]
    current_mod = importlib.import_module(mod_name)
    # print "Current Mod", current_mod
    # print dir(current_mod)
    for rig_module in current_mod.exported_rig_modules:
        print rig_module
        all_rig_modules[rig_module.__name__] = rig_module

print "all_rig_modules", all_rig_modules
