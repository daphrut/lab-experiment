# Function to create variable(s) from cell(s) in individual survey files
def create_var(ws, labs, mask, var_name,
               cell,
               multiple_cells=False,
               no_variables=False,
               comment_cell=None,
               fc_cell=None) :

    # Multiple cells
    if multiple_cells:
        cells = ws[cell]  # cell range
        values = [c.value for row in cells for c in row]
        values = [v for v in values]

        if comment_cell:
            comment_cells = ws[comment_cell] # comment range
            comment_values = [c.value for row in comment_cells for c in row]
            comment_values = [v for v in comment_values]

        if fc_cell:
            fc_cells = ws[fc_cell] # free text range
            fc_values = [c.value for row in fc_cells for c in row]
            fc_values = [v for v in fc_values]

        # Create separate variables per cell (cell, comment, free text)
        if no_variables: 
            for i, v in enumerate(values, start=1):
                labs.loc[mask, f"{var_name}_{i}"] = v

            if comment_cell:
                for i, v in enumerate(comment_values, start=1):
                    labs.loc[mask, f"{var_name}_{i}_co"] = v
            
            if fc_cell:
                for i, v in enumerate(fc_values, start=1):
                    labs.loc[mask, f"{var_name}_{i}_fc"] = v

        # Create single variable with all cells joined by ";"
        else:
            labs.loc[mask, var_name] = ";".join(str(v) for v in values if v not in (None, ""))

            if comment_cell:
                labs.loc[mask, f"{var_name}_co"] = ";".join(str(v) for v in comment_values if v not in (None, ""))
            
            if fc_cell:
                labs.loc[mask, f"{var_name}_fc"] = ";".join(str(v) for v in fc_values if v not in (None, ""))

    # Single cell
    else:
        v = ws[cell].value
        labs.loc[mask, var_name] = v

        # Comment
        if comment_cell:
            v = ws[comment_cell].value
            labs.loc[mask, f"{var_name}_co"] = v

        # Free text response
        if fc_cell:
            v = ws[fc_cell].value
            labs.loc[mask, f"{var_name}_fc"] = v