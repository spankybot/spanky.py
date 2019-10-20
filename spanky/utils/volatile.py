# Save volatile data, per bot session
vol_stor = {}

def set_vdata(key, val):
    vol_stor[key] = val

def get_vdata(key):
    if key in vol_stor:
        return vol_stor[key]
    else:
        return None