import numpy as np
import pandas as pd


def normalize_weights(edges, id_col_i, id_col_j, weight_col, all_ids, symmetric=True):
    """
    Build a row-normalized labgroupid x labgroupid weight matrix from an edge list.

    Parameters
    ----------
    edges       : DataFrame with columns [id_col_i, id_col_j, weight_col]
    id_col_i    : column name for the first labgroupid in each edge
    id_col_j    : column name for the second labgroupid in each edge
    weight_col  : column name for the raw (unnormalized) edge weight
    all_ids     : full set of labgroupids to include as rows/columns (isolates
                  included, edges referencing ids outside this set are dropped)
    symmetric   : if True (default), each edge contributes to both wij and wji

    Returns
    -------
    df indexed and columned by all_ids. Each row sums to 1, except rows
    for labgroups with no ties to another id in all_ids, which are all zero.
    Since treated in {0,1}, this guarantees compute_exposure() returns Si in [0,1].
    """
    all_ids = list(all_ids)
    W = pd.DataFrame(0.0, index=all_ids, columns=all_ids)

    valid = edges[edges[id_col_i].isin(all_ids) & edges[id_col_j].isin(all_ids)]
    for i, j, w in valid[[id_col_i, id_col_j, weight_col]].itertuples(index=False):
        W.loc[i, j] += w
        if symmetric:
            W.loc[j, i] += w

    row_sums = W.sum(axis=1)
    return W.div(row_sums.replace(0, np.nan), axis=0).fillna(0)


def compute_exposure(weight_matrix, treated):
    """
    Si = sum_j wij * treated_j.

    Parameters
    ----------
    weight_matrix : row-normalized labgroupid x labgroupid df (see
                    normalize_weights)
    treated       : labgroupid-indexed Series of 0/1 treatment status

    Returns
    -------
    labgroupid-indexed Series named "S", in [0,1] given a row-normalized
    weight_matrix and binary treated.
    """
    treated_aligned = treated.reindex(weight_matrix.columns).fillna(0)
    exposure = weight_matrix.values @ treated_aligned.values
    return pd.Series(exposure, index=weight_matrix.index, name="S")


def combine_measures(weight_matrices):
    """
    Elementwise-average several row-normalized weight matrices (all indexed and
    columned identically) into a single combined, re-normalized weight matrix.

    Not yet used by any regression spec - available for the future "combined
    exposure" spec once multiple proximity measures are ready.
    """
    stacked = sum(weight_matrices) / len(weight_matrices)
    row_sums = stacked.sum(axis=1)
    return stacked.div(row_sums.replace(0, np.nan), axis=0).fillna(0)
