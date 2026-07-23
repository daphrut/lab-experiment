# Functions to match ZORA publication creators to labgroupids:
#       (1) Parse each ZORA creator entry ("Surname, Firstname Middle") using the reliable
#           surname/given boundary at the comma
#       (2) Compare against manually-cleaned researcher surname_clean/first_name_clean fields:
#           surname must match exactly (never via initial), first name may fall back to an
#           initial-letter match (e.g. "S." matching "Stuart")
#       (3) Aggregate matches back up to one row per publication, tracking match confidence
#           and flagging creator names that ambiguously match more than one labgroupid

import pandas as pd
import numpy as np
import re
import unicodedata

CONFIDENCE_RANK = {"exact": 0, "initial": 1}


def normalize_token(token):
    token = unicodedata.normalize("NFKD", token)
    token = token.encode("ascii", "ignore").decode()
    token = re.sub(r"[^a-zA-Z-]", "", token)
    return token.lower()


def normalize_tokens(raw):
    if pd.isna(raw):
        return []
    return [t for t in (normalize_token(tok) for tok in raw.split()) if t]


def parse_creator_entry(raw_entry):
    # Surname is always the part before the first comma; given/middle names follow
    if "," in raw_entry:
        surname_part, given_part = raw_entry.split(",", 1)
    else:
        surname_part, given_part = raw_entry, ""

    surname_tokens = normalize_tokens(surname_part)
    given_tokens = normalize_tokens(given_part)
    first_name = given_tokens[0] if given_tokens else None

    return surname_tokens, first_name


def match_publications_to_labs(
    pub_df, id_col, creator_col, researchers_df, surname_col="surname_clean", first_name_col="first_name_clean"
):

    # Step 1: Split creators into one row per publication-creator pair
    creators = pub_df[[id_col, creator_col]].copy()
    creators[creator_col] = creators[creator_col].str.split(" | ", regex=False)
    creators = creators.explode(creator_col).dropna(subset=[creator_col]).reset_index(drop=True)

    # Step 2: Strip ORCID/other suffix (everything from the first ";" onward, if present)
    creators["creator_key"] = creators[creator_col].str.split(";", n=1).str[0].str.strip()

    # Step 3: Parse unique creator entries into (surname_tokens, first_name)
    unique_creators = pd.Series(creators["creator_key"].dropna().unique(), name="creator_key")
    parsed = unique_creators.apply(parse_creator_entry)
    creator_surname_map = dict(zip(unique_creators, parsed.apply(lambda x: x[0])))
    creator_first_name_map = dict(zip(unique_creators, parsed.apply(lambda x: x[1])))

    # Step 4: Prep researchers (one row per person), normalizing surname/first name fields
    researchers = (
        researchers_df[["labgroupid", surname_col, first_name_col]]
        .dropna(subset=[surname_col, first_name_col])
        .drop_duplicates()
        .reset_index(drop=True)
    )
    researchers["researcher_idx"] = researchers.index
    researchers["surname_tokens"] = researchers[surname_col].apply(normalize_tokens)
    researchers["first_name_norm"] = researchers[first_name_col].apply(normalize_token)

    # Step 5: Build blocking index on surname tokens and merge to find candidate pairs
    creator_token_rows = [
        (key, tok) for key, toks in creator_surname_map.items() for tok in toks
    ]
    creator_token_df = pd.DataFrame(creator_token_rows, columns=["creator_key", "token"])

    researcher_token_rows = [
        (row.researcher_idx, tok) for row in researchers.itertuples() for tok in row.surname_tokens
    ]
    researcher_token_df = pd.DataFrame(researcher_token_rows, columns=["researcher_idx", "token"])

    candidates = creator_token_df.merge(researcher_token_df, on="token", how="inner")
    candidates = candidates[["creator_key", "researcher_idx"]].drop_duplicates()

    # Step 6: Verify candidates - surname must be a full subset match (exact), first name exact or initial
    def verify(row):
        surname_tokens = set(creator_surname_map[row["creator_key"]])
        first_name = creator_first_name_map[row["creator_key"]]
        researcher_row = researchers.loc[row["researcher_idx"]]

        if not set(researcher_row["surname_tokens"]).issubset(surname_tokens):
            return False, None
        if first_name is None:
            return False, None
        if first_name == researcher_row["first_name_norm"]:
            return True, "exact"
        if len(first_name) == 1 and researcher_row["first_name_norm"].startswith(first_name):
            return True, "initial"
        return False, None

    if not candidates.empty:
        results = candidates.apply(verify, axis=1, result_type="expand")
        candidates["is_match"] = results[0]
        candidates["match_confidence"] = results[1]
        confirmed = candidates[candidates["is_match"]].merge(
            researchers[["researcher_idx", "labgroupid"]], on="researcher_idx", how="left"
        )
        confirmed = confirmed[["creator_key", "labgroupid", "match_confidence"]]
    else:
        confirmed = pd.DataFrame(columns=["creator_key", "labgroupid", "match_confidence"])

    # Step 7: Flag creator names that individually match more than one distinct labgroupid
    creator_lab_counts = confirmed.groupby("creator_key")["labgroupid"].nunique()
    ambiguous_creator_keys = set(creator_lab_counts[creator_lab_counts > 1].index)

    # Step 8: Map confirmed matches back onto every publication row containing that creator string
    creators = creators.merge(confirmed, on="creator_key", how="left")

    # Step 9: Aggregate back up to one row per publication
    def aggregate(group):
        matched = group.dropna(subset=["labgroupid"]).copy()
        matched["labgroupid"] = matched["labgroupid"].astype(researchers_df["labgroupid"].dtype)

        # Best (lowest-rank) confidence per labgroupid, in case multiple creators/tiers matched the same lab
        best_confidence = (
            matched.assign(_rank=matched["match_confidence"].map(CONFIDENCE_RANK))
            .sort_values("_rank")
            .drop_duplicates(subset=["labgroupid"], keep="first")
        )

        ambiguous_creators = sorted(
            set(group.loc[group["creator_key"].isin(ambiguous_creator_keys), "creator_key"])
        )

        return pd.Series({
            "matched_labgroupids": sorted(best_confidence["labgroupid"].tolist()),
            "match_confidence": best_confidence.sort_values("labgroupid")["match_confidence"].tolist(),
            "ambiguous_creators": ambiguous_creators,
        })

    out = creators.groupby(id_col, sort=False).apply(aggregate).reset_index()

    return out
