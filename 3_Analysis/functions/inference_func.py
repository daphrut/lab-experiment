import numpy as np


def wild_cluster_bootstrap_pval(fit, param, cluster="labgroupid", reps=999, seed=None):
    """
    Wild cluster bootstrap p-value for one coefficient, via pyfixest's native
    Feols.wildboottest() (Rademacher weights, null imposed, default "11"
    bootstrap type) - a finite-sample alternative to the model's asymptotic
    cluster-robust p-value, as a robustness check on it.

    fit     : a fitted pyfixest Feols object
    param   : coefficient name to test, e.g. "treated:post"
    cluster : clustering variable (should match the model's own CRV1 cluster)
    reps    : number of bootstrap iterations
    seed    : for reproducibility

    Returns the bootstrap p-value (float).
    """
    result = fit.wildboottest(param=param, reps=reps, cluster=cluster, seed=seed)
    return float(result["Pr(>|t|)"])


def randomization_inference_pval(
    df,
    fit_fn,
    param,
    observed_coef,
    strata_var="faculty_old",
    unit_var="labgroupid",
    treatment_var="treated",
    reps=999,
    seed=None,
    recompute_fn=None,
    alternative="two-sided",
):
    """
    Randomization inference (Fisher exact) p-value for one coefficient,
    replicating this project's actual randomization design: 50/50
    treatment/control, stratified by strata_var: "faculty_old".

    df             : full panel/analysis dataframe used to fit the real model
    fit_fn         : callable(df) -> fitted pyfixest object, refitting the
                     exact same specification on a (possibly modified) copy
                     of df - see recompute_fn for specs needing a derived
                     variable recomputed from the permuted treatment
    param          : coefficient name to extract from each placebo fit, e.g.
                     "treated:post"
    observed_coef  : the real model's estimated coefficient (from the
                     actual, unpermuted fit) - the test statistic the
                     placebo distribution is compared against
    strata_var     : randomization stratum column (default "faculty_old")
    unit_var       : randomization unit column (default "labgroupid")
    treatment_var  : treatment column to permute (default "treated")
    reps           : number of placebo reassignments
    seed           : for reproducibility
    recompute_fn   : optional callable(df_with_permuted_treatment) -> df,
                     called after permuting treatment_var but before
                     fit_fn, to recompute any variable that itself depends
                     on the (now-permuted) treatment assignment of OTHER
                     units - e.g. 4_5's spillover exposure S_collaboration,
                     via spillover_helpers.compute_exposure(). Not needed
                     for specs where only treatment_var itself enters the
                     formula.
    alternative    : "two-sided" (default) - share of |placebo| >= |observed|.
                     "greater" / "less" for one-sided tests.

    Returns (p_value, placebo_coefs) - the RI p-value and the full array of
    placebo coefficients. p_value uses the standard (exceedances + 1) / (reps + 1) 
    correction, since the actual, observed assignment is itself one valid draw 
    from the randomization distribution - without it, a placebo distribution 
    that happens to never exceed the observed effect would wrongly report 
    p = 0 rather than the correct 1 / (reps + 1) (not observed in this
    many draws).
    """
    rng = np.random.default_rng(seed)

    unit_df = df[[unit_var, strata_var, treatment_var]].drop_duplicates(unit_var).set_index(unit_var)

    placebo_coefs = np.empty(reps)
    for r in range(reps):
        permuted = unit_df[treatment_var].copy()
        for _, idx in unit_df.groupby(strata_var).groups.items():
            vals = unit_df.loc[idx, treatment_var].to_numpy().copy()
            rng.shuffle(vals)
            permuted.loc[idx] = vals

        df_placebo = df.copy()
        df_placebo[treatment_var] = df_placebo[unit_var].map(permuted)
        if recompute_fn is not None:
            df_placebo = recompute_fn(df_placebo)

        fit_placebo = fit_fn(df_placebo)
        placebo_coefs[r] = fit_placebo.coef().loc[param]

    if alternative == "two-sided":
        exceed = (np.abs(placebo_coefs) >= abs(observed_coef)).sum()
    elif alternative == "greater":
        exceed = (placebo_coefs >= observed_coef).sum()
    elif alternative == "less":
        exceed = (placebo_coefs <= observed_coef).sum()
    else:
        raise ValueError(f"Unknown alternative: {alternative}")

    p_value = (exceed + 1) / (reps + 1)

    return p_value, placebo_coefs
