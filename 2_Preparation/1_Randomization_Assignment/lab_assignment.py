import pandas as pd
import numpy as np 

# Assignment function
def assign_enumerators(labs_df, enum_df, n_treat = 3, n_control = 3, seed = 110):
    """ Assign enumerators to lab groups.
    
    - Each enumerator is assigned to 3 treatment and 3 control lab groups by default.
    - Takes into account n_treated and n_control for each enumerator if given.
    - Takes into account 2 location restrictions.
    - No lab is assigned twice.
    
    Returns:
    - assignments: labs with assigned enumerators
    - leftover_treatment: treatment labs without enumerators
    - leftover_control: control labs without enumerators
    """
    rng = np.random.RandomState(seed)

    leftover_labs = labs_df.copy()
    assignments = pd.DataFrame()

    for _, enum in enum_df.iterrows():
        possible_labs = leftover_labs.copy()

        # Use enum-specific n_treated/n_control if available
        n_treat = enum.get("n_treated", n_treat)
        n_control = enum.get("n_control", n_control)

        # Apply location restrictions
        if enum.get("restriction_sch", 0) == 1:
            possible_labs = possible_labs[possible_labs["Location SCH"] == 1]
        if enum.get("restriction_bot", 0) == 1:
            possible_labs = possible_labs[possible_labs["Location BOT"] == 1]

        # Separate treatment and control labs
        treatment_labs = possible_labs[possible_labs["Treatment Status"] == "treatment"]
        control_labs = possible_labs[possible_labs["Treatment Status"] == "control"]

        # Assign labs, checking if enough labs are available
        n_leftover_treat = len(treatment_labs)
        n_leftover_control = len(control_labs)
        if n_leftover_treat < n_treat:
            if n_leftover_control < n_control: # Not enough T and C labs
                print(f"Warning: Only {n_leftover_treat} treatment and {n_leftover_control} control labs available for enumerator.")
                assigned_treat = treatment_labs
                assigned_control = control_labs
            else:  # Not enough T labs
                print(f"Warning: Only {n_leftover_treat} treatment labs available for enumerator.")
                assigned_treat = treatment_labs
                assigned_control = control_labs.sample(n=6-n_leftover_treat, random_state=rng, replace=False)
        elif n_leftover_control < n_control: # Not enough C labs
            print(f"Warning: Only {n_leftover_control} control labs available for enumerator.")
            assigned_control = control_labs
            assigned_treat = treatment_labs.sample(n=6-n_leftover_control, random_state=rng, replace=False)
        else: # Enough T and C labs
            assigned_treat = treatment_labs.sample(n=n_treat, random_state=rng, replace=False)
            assigned_control = control_labs.sample(n=n_control, random_state=rng, replace=False)

        assigned = pd.concat([assigned_treat, assigned_control])

        # Assign enumerator info
        assigned = assigned.copy()
        assigned["enum_lastname"] = enum["lastname"]
        assigned["enum_firstname"] = enum["firstname"]
        assigned["enum_id"] = enum["id"]
        assigned["enum_email"] = enum["email_cleaned"]
        assigned["enum_foldername"] = enum["foldername"]
        assigned["enum_restriction"] = enum["restriction"]

        # Append to assignments and remove from leftover labs
        assignments = pd.concat([assignments, assigned])

        # Remove assigned labs from leftover_labs by labgroupid
        assigned_lab_ids = assigned["labgroupid"].tolist()
        leftover_labs = leftover_labs[~leftover_labs["labgroupid"].isin(assigned_lab_ids)]

    # Leftover labs
    leftover_treatment = leftover_labs[leftover_labs["Treatment Status"] == "treatment"]
    leftover_control = leftover_labs[leftover_labs["Treatment Status"] == "control"]

    return assignments, leftover_treatment, leftover_control
