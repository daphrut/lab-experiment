def fill_with_equipment_mode(
    df,
    value_col,
    equipment_value,
    equipment_col="equipment",
    unknown_value="Unknown",
    groupby_cols=None,
    fallback_to_equipment_mode=True,
):
    """
    Fill missing/Unknown values in value_col for one equipment type.

    By default, fills using the mode within the selected equipment type.
    Optionally, compute mode within additional grouping column(s), e.g.:
    groupby_cols="institute" or groupby_cols=["institute", "survey"].
    """
    is_target_equipment = df[equipment_col] == equipment_value
    valid = is_target_equipment & df[value_col].notna() & (df[value_col] != unknown_value)

    if not valid.any():
        return df

    fill_mask = is_target_equipment & (
        df[value_col].isna() | (df[value_col] == unknown_value)
    )
    if not fill_mask.any():
        return df

    # Backwards-compatible path: equipment-level mode only.
    if groupby_cols is None:
        mode = df.loc[valid, value_col].mode().iloc[0]
        df.loc[fill_mask, value_col] = mode
        return df

    if isinstance(groupby_cols, str):
        groupby_cols = [groupby_cols]

    # Build per-group modes within the selected equipment.
    mode_by_group = (
        df.loc[valid, groupby_cols + [value_col]]
        .groupby(groupby_cols, dropna=False)[value_col]
        .agg(lambda s: s.mode().iloc[0])
    )

    fallback_mode = None
    if fallback_to_equipment_mode:
        fallback_mode = df.loc[valid, value_col].mode().iloc[0]

    fill_index = df.index[fill_mask]
    for idx in fill_index:
        if len(groupby_cols) == 1:
            key = df.at[idx, groupby_cols[0]]
        else:
            key = tuple(df.loc[idx, groupby_cols].tolist())

        fill_value = mode_by_group.get(key, fallback_mode)
        if fill_value is not None:
            df.at[idx, value_col] = fill_value

    return df
