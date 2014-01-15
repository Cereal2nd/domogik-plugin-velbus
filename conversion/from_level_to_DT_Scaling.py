def from_level_to_DT_Scaling(x):
    # 0 - 255 translated to 0 - 100
    return round(int(x) / 255 * 100)
