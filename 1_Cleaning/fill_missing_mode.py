import numpy as np


def fill_with_equipment_mode(
    df,
    value_col,
    equipment_value,
    equipment_col="equipment",
    unknown_value="Unknown",
):
    """Fill missing/Unknown values in value_col using mode for one equipment type."""
    is_target_equipment = df[equipment_col] == equipment_value
    valid = is_target_equipment & df[value_col].notna() & (df[value_col] != unknown_value)

    if not valid.any():
        return df

    mode = df.loc[valid, value_col].mode().iloc[0]

    fill_mask = is_target_equipment & (
        df[value_col].isna() | (df[value_col] == unknown_value)
    )

    df.loc[fill_mask, value_col] = mode
    return df
