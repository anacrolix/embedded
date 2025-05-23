import network

# Converts network.WLAN status integer to its constant name.
def wlan_status_name(status):
    prefix = 'STAT_'
    for name in dir(network):
        if not name.startswith(prefix):
            continue
        value = getattr(network, name)
        if value == status:
            return name[len(prefix):].lower()
    raise KeyError(status)