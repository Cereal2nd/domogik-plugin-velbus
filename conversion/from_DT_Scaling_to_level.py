def from_DT_Scaling_to_level(x):
    # 0 - 100 translated to 0 - 255
    return round(int(x) / 100 * 255)

