import numpy as np
import pandas as pd

# Assign set temperature to the closest setpoint.
def assign_set_temp(temp, setpoints):
    if pd.isna(temp):
        return np.nan

    valid_setpoints = [sp for sp in setpoints if not pd.isna(sp)]
    if not valid_setpoints:
        return np.nan

    temp_value = float(temp)
    return min(valid_setpoints, key=lambda sp: abs(temp_value - float(sp)))