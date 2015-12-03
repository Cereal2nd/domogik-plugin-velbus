def from_level_to_DT_Switch(x):
    if x == '255' or x == 255:
        return int(1)
    if x == '0' or x == 0:
        return int(0)

