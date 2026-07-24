# ============================================================================
# Function to match publication creators to labgroupids.
#
# THE PROBLEM
# -----------
# We want to know, for each publication, which of our lab's researchers (if
# any) are among its authors - and therefore which labgroupid(s) it belongs to.
#
# This is fiddly for three separate reasons, each handled separately below:
#
#   1. A creator string can have multiple authors (separated by " | "), and
#      some authors have an ORCID web address tacked on after a ";".
#
#   2. The same name can be spelled in more than one way. We can normalize
#      some of these differences deterministically (e.g. hyphen vs space), but
#      others require guessing which convention the author used. In particular,
#      we deal explicitly with umlaut conventions e.g. Müller/Muller/Mueller.
#
#   3. First names are sometimes just an initial ("J." instead of "John"),
#      so first-name matching has to check for these matches too.
#
#   4. Some people have more than one given name (e.g. "Mark Duncan"). Only
#      the primary (first) one is required to match; a second given name is
#      only checked as an informational flag, never required - a citation
#      might drop it entirely.
#
# THE APPROACH
# ------------
#
#   1. Surnames and first/middle names are already split in the researcher
#      data. ZORA always writes creators as "Surname, Firstname (Middle)".
#
#   2. We separate the ZORA data into one row per publication/creator pair.
#      We normalize each creator's surname and first name. For any umlauts,
#      we generate every plausible spelling of the surname and first name.
#
#   3. We normalize the researcher data in the same way, generating every
#      plausible spelling of each researcher's surname and first name.
#
#   4. We match surnames by checking if any of the researcher's plausible
#      spellings match any of the creator's. For first names, only the
#      primary given name (token 1) has to match, exactly or via initial;
#      a second given name, if present on either side, is checked too but
#      only reported as a flag (middle_name_match), not required to match.
#
# ============================================================================

import pandas as pd
import re
import unicodedata
from collections import namedtuple

# Ranking used to pick the "best" (most confident) match when the same
# labgroupid is reachable via more than one creator/tier on one publication.
CONFIDENCE_RANK = {"exact": 0, "initial": 1}

# A single plausible spelling of a name field (surname, or first name),
# together with a note of why it's a guess rather than the literal text:
#   tokens          -> the normalized word(s) for this spelling,
#                      e.g. ["smith", "jones"]
#   umlaut_variant  -> True if we only reached this spelling by assuming a
#                      different umlaut convention variant ("ü" vs "ue"). 
#                      False for the "no guessing" (literal) spelling.

Candidate = namedtuple("Candidate", ["tokens", "umlaut_variant"])

# ----------------------------------------------------------------------------
# SECTION 1 - generic, deterministic text normalization
#
# This is the "no guessing" pipeline applied to every piece of text on both
# sides (creators and researchers): make special characters harmless, drop
# punctuation, lowercase, split into words. Always produces one answer.
# ----------------------------------------------------------------------------
#
# Characters with no spelling ambiguity in plain ASCII - there is one clear 
# transliteration, so we just substitute and move on (unlike umlauts, where
# two conventions are both common enough that we have to check both).
_DETERMINISTIC_SUBSTITUTIONS = [
    # Accents that have a single, standard ASCII spelling
    ("ß", "ss"),
    ("ø", "o"), ("Ø", "O"),
    ("œ", "oe"), ("Œ", "OE"),
    ("æ", "ae"), ("Æ", "AE"),
    # A hyphen and a space are interchangeable in surnames
    ("-", " "),
]


def _apply_deterministic_substitutions(text):
    """Replace characters that have one obvious, undisputed ASCII spelling."""
    for old, new in _DETERMINISTIC_SUBSTITUTIONS:
        text = text.replace(old, new)
    return text


def normalize_token(token):
    """
    Reduce a single word to a plain-ASCII, lowercase form for comparison:
    strip remaining accents (e.g. "é"->"e", "ñ"->"n" - anything with a
    standard Unicode decomposition) and drop punctuation. By the time this
    runs, hyphens have already been turned into spaces (see
    _DETERMINISTIC_SUBSTITUTIONS above), so a token should never contain one -
    we still just discard any stray punctuation here rather than assume that.
    """
    # NFKD decomposition splits an accented letter into its plain letter plus
    # a separate "combining accent" mark (e.g. "é" -> "e" + combining acute).
    # Encoding to ASCII and ignoring anything that doesn't fit then drops the
    # accent mark, leaving just the plain letter.
    token = unicodedata.normalize("NFKD", token)  # Replace accents with plain letter
    token = token.encode("ascii", "ignore").decode()  # Replace non-ASCII with nothing
    token = re.sub(r"[^a-zA-Z]", "", token)  # Drop punctuation
    return token.lower()  # Lowercase


def normalize_tokens(raw):
    """Split a raw text field on whitespace and normalize every resulting word."""
    if pd.isna(raw):
        return []
    return [t for t in (normalize_token(tok) for tok in raw.split()) if t]


# ----------------------------------------------------------------------------
# SECTION 2 - variant generation (the umlaut guessing)
#
# For a name field on either side (ZORA or researchers), generate every
# spelling that could be plausibly used for it, tagged with why it's a guess, 
# so a downstream match can report exactly which assumption it relied on.
# ----------------------------------------------------------------------------

# Literal umlaut character -> (plain-strip, digraph) e.g. "ü" -> ("u", "ue")
_LITERAL_UMLAUT_OPTIONS = {
    "ü": ("u", "ue"), "Ü": ("U", "Ue"),
    "ö": ("o", "oe"), "Ö": ("O", "Oe"),
    "ä": ("a", "ae"), "Ä": ("A", "Ae"),
}

# Digraph -> plain-strip e.g. "ue" -> "u"
_ASCII_DIGRAPH_COLLAPSE = {
    "ue": "u", "Ue": "U",
    "oe": "o", "Oe": "O",
    "ae": "a", "Ae": "A",
}

def _branch_umlaut(text):
    """
    Scan the text left to right. At every position that looks like an umlaut
    (either a literal ü/ö/ä, or an ASCII "ue"/"oe"/"ae" that might be a
    transliterated one), branch into every plausible spelling at that spot.
    Elsewhere, characters are just carried through unchanged.

    Returns a list of (text_variant, used_umlaut_guess) pairs. When the text
    contains no umlaut-like spot at all, this returns exactly one pair - the
    original text, unguessed (flag False).
    """
    # We build up the list of (partial_string, guess_flag_so_far) options as
    # we scan, character by character, letting the list of options grow
    # (branch) whenever we hit an ambiguous spot.
    options = [("", False)]
    i = 0
    while i < len(text):

        # Literal umlaut character: branch into plain-strip and digraph
        literal = _LITERAL_UMLAUT_OPTIONS.get(text[i])
        if literal is not None:
            plain_opt, digraph_opt = literal
            options = (
                [(s + plain_opt, flag) for (s, flag) in options] +
                [(s + digraph_opt, True) for (s, flag) in options]
            )
            i += 1
            continue

        # ASCII digraph: branch into plain-strip and literal
        two_char = text[i:i + 2]
        collapsed = _ASCII_DIGRAPH_COLLAPSE.get(two_char)
        if collapsed is not None:
            options = (
                [(s + two_char, flag) for (s, flag) in options] +
                [(s + collapsed, True) for (s, flag) in options]
            )
            i += 2
            continue

        # Ordinary character: just carry it forward on every option unchanged
        options = [(s + text[i], flag) for (s, flag) in options]
        i += 1

    return options


def generate_field_variants(raw_field):
    """
    Generate every plausible normalized spelling of one name field (a
    surname, or a first/given name - from either the creator side or the
    researcher side), each tagged with whether it required an
    umlaut-convention guess.

    Returns a list of Candidate(tokens, umlaut_variant). A name with more than
    one umlaut-like spot combines all of them (Cartesian product).
    """
    if pd.isna(raw_field):
        return []

    # Normalize every umlaut-guess variant down to its final token list.
    candidates = []
    for umlaut_text, used_umlaut in _branch_umlaut(raw_field):
        substituted = _apply_deterministic_substitutions(umlaut_text)
        tokens = normalize_tokens(substituted)
        if tokens:
            candidates.append(Candidate(tokens=tokens, umlaut_variant=used_umlaut))

    return candidates


# ----------------------------------------------------------------------------
# SECTION 3 - creator-side (ZORA) parsing
#
# One creator string always splits into exactly one surname part and one
# given-name part - ZORA's comma is trusted to always be the correct
# boundary. Each part then goes through the umlaut variant generation.
# ----------------------------------------------------------------------------

def parse_creator_entry(raw_entry):
    """
    Split one ZORA creator entry at its comma, then generate every plausible
    spelling of each half. Returns (surname_candidates, firstname_candidates)
    - both lists of Candidate(tokens, umlaut_variant).

    firstname_candidates' tokens can include a second given name or a middle
    name (e.g. "Mark Duncan" -> ["mark", "duncan"]) - every token is compared
    against the researcher's given-name tokens later on, since a citation
    might use any one of them, spelled out or abbreviated to an initial, not
    necessarily the first.
    """
    if "," in raw_entry:
        # Split at the first comma
        surname_part, given_part = raw_entry.split(",", 1)
    else:
        # If no comma, treat whole thing as surname
        surname_part, given_part = raw_entry, ""

    surname_candidates = generate_field_variants(surname_part)
    firstname_candidates = generate_field_variants(given_part)

    return surname_candidates, firstname_candidates


# ----------------------------------------------------------------------------
# SECTION 4 - the matching pipeline itself
# ----------------------------------------------------------------------------

def match_publications_to_labs(
    pub_df,
    id_col,
    creator_col,
    researchers_df,
    surname_col="responsible_person_surname",
    first_name_col="responsible_person_firstname",
):
    """
    For every publication in pub_df, find which labgroupid(s) (if any) have a
    researcher among the publication's creators.

    pub_df:          one row per publication; must have id_col and creator_col.
    id_col:          column that uniquely identifies a publication (e.g. "relation").
    creator_col:     the raw ZORA creator string, "Surname, First | Surname2, First2; orcid...".
    researchers_df:  one row per researcher, with a labgroupid column plus the
                     manually-cleaned surname_col / first_name_col.

    Returns one row per publication (id_col) with:
        matched_labgroupids -> sorted list of distinct labgroupids matched via
                                ANY creator on this publication (can legitimately
                                be longer than 1 - a paper can have co-authors
                                from different labs; that's normal, not an error)
        match_confidence     -> parallel list, "exact" or "initial", scoped to
                                the PRIMARY (first) given-name comparison for
                                that labgroupid
        umlaut_variant        -> parallel list of booleans: did matching that
                                labgroupid require assuming an umlaut<->digraph
                                swap, on either the creator or researcher side?
        middle_name_match     -> parallel list of booleans: for a researcher
                                with a second given name / middle name (or a
                                citation that includes one), did it also line
                                up? This is informational only - it never
                                affects whether something counts as a match,
                                since a citation might drop a middle name
                                entirely (or vice versa).
    """

    # ---- Step 1: one row per (publication, individual creator) ------------
    # A publication can list several authors separated by " | "; explode so
    # each gets its own row, still tagged with which publication it came from.
    creators = pub_df[[id_col, creator_col]].copy()
    creators[creator_col] = creators[creator_col].str.split(" | ", regex=False)
    creators = creators.explode(creator_col).dropna(subset=[creator_col]).reset_index(drop=True)

    # ---- Step 2: strip a trailing ORCID/other suffix -----------------------
    # When present, it's separated by ";" - e.g. "Smith, John; https://orcid.org/...".
    # Not every entry has one, so this is a no-op for those that don't.
    creators["creator_key"] = creators[creator_col].str.split(";", n=1).str[0].str.strip()

    # ---- Step 3: parse each unique creator string ------------------------
    # Many publications share co-authors, so working on unique strings avoids
    # redoing the same parse over and over. Each unique creator now maps to a
    # list of surname candidates and a list of given-name candidates (usually
    # each list has just one element - branching only happens for names that
    # actually contain an umlaut-like spot).
    unique_creators = pd.Series(creators["creator_key"].dropna().unique(), name="creator_key")
    parsed = unique_creators.apply(parse_creator_entry)
    creator_surname_candidates_map = dict(zip(unique_creators, parsed.apply(lambda x: x[0])))
    creator_firstname_candidates_map = dict(zip(unique_creators, parsed.apply(lambda x: x[1])))

    # ---- Step 4: prep the researcher table ---------------------------------
    # One row per person, with every plausible spelling of their surname and
    # first name precomputed (see Section 2).
    researchers = (
        researchers_df[["labgroupid", surname_col, first_name_col]]
        .dropna(subset=[surname_col, first_name_col])
        .drop_duplicates()
        .reset_index(drop=True)
    )
    researchers["researcher_idx"] = researchers.index
    researchers["surname_candidates"] = researchers[surname_col].apply(generate_field_variants)
    researchers["first_name_candidates"] = researchers[first_name_col].apply(generate_field_variants)

    # ---- Step 5: blocking - cheaply narrow down candidate pairs ------------
    # Checking every creator string against every researcher's full candidate
    # list would work but is wasteful. Instead, index every token that
    # appears in ANY surname candidate - on both the researcher side and now
    # the creator side too - then use a plain pd.merge on shared tokens to
    # find just the (creator, researcher) pairs worth fully verifying. A
    # creator with zero surname-token overlap with any researcher is
    # discarded for free right here.
    researcher_token_rows = [
        (row.researcher_idx, tok)
        for row in researchers.itertuples()
        for cand in row.surname_candidates
        for tok in cand.tokens
    ]
    researcher_token_df = pd.DataFrame(
        researcher_token_rows, columns=["researcher_idx", "token"]
    ).drop_duplicates()

    creator_token_rows = [
        (key, tok)
        for key, cands in creator_surname_candidates_map.items()
        for cand in cands
        for tok in cand.tokens
    ]
    creator_token_df = pd.DataFrame(creator_token_rows, columns=["creator_key", "token"]).drop_duplicates()

    candidate_pairs = creator_token_df.merge(researcher_token_df, on="token", how="inner")
    candidate_pairs = candidate_pairs[["creator_key", "researcher_idx"]].drop_duplicates()

    # ---- Step 6: verify each candidate pair --------------------------------
    def verify(row):
        """
        Full check for one (creator, researcher) candidate pair. Surname must
        match exactly (as a full set of tokens) via some combination of a
        researcher candidate and a creator candidate.

        First name: only the PRIMARY given name (token[0] on each side) is
        required to match, exactly or via an initial (creator side only - the
        researcher's manually-entered given names are never just an initial).
        If either side also has a second given name / middle name (e.g.
        "Mark Duncan"), that's checked too, but only as a non-blocking
        `middle_name_match` flag - it doesn't gate whether this counts as a
        match, since a citation might drop a middle name entirely, or the
        researcher's own middle name might just not appear anywhere in it.

        Among all combinations that pass, we always keep the "cleanest"
        (fewest guesses) one, so the reported flags reflect the least
        speculative explanation available.
        """
        creator_surname_cands = creator_surname_candidates_map[row["creator_key"]]
        creator_firstname_cands = creator_firstname_candidates_map[row["creator_key"]]
        researcher_row = researchers.loc[row["researcher_idx"]]

        # --- surname: best (fewest-guesses) matching combination ---
        best_surname_umlaut = None
        for r_cand in researcher_row["surname_candidates"]:
            r_tokens = set(r_cand.tokens)
            for c_cand in creator_surname_cands:
                if r_tokens.issubset(set(c_cand.tokens)):
                    combined = r_cand.umlaut_variant or c_cand.umlaut_variant
                    if best_surname_umlaut is None or combined < best_surname_umlaut:
                        best_surname_umlaut = combined

        if best_surname_umlaut is None or not creator_firstname_cands:
            return False, None, None, None

        # --- first name: only the primary (first) given name is required ---
        best_first = None  # (score_tuple, tier, combined_umlaut, middle_name_match)
        for r_cand in researcher_row["first_name_candidates"]:
            if not r_cand.tokens:
                continue
            r_first, r_rest = r_cand.tokens[0], r_cand.tokens[1:]

            for c_cand in creator_firstname_cands:
                if not c_cand.tokens:
                    continue
                c_first, c_rest = c_cand.tokens[0], c_cand.tokens[1:]

                if r_first == c_first:
                    tier = "exact"
                elif len(c_first) == 1 and r_first.startswith(c_first):
                    tier = "initial"
                else:
                    continue

                # Non-blocking secondary check: does a second given name /
                # middle name on either side also line up? Doesn't affect
                # whether this counts as a match, just reported as a flag.
                middle_name_match = any(
                    rt == ct or (len(ct) == 1 and rt.startswith(ct))
                    for rt in r_rest
                    for ct in c_rest
                )

                combined_umlaut = r_cand.umlaut_variant or c_cand.umlaut_variant
                score = (0 if tier == "exact" else 1, combined_umlaut)
                if best_first is None or score < best_first[0]:
                    best_first = (score, tier, combined_umlaut, middle_name_match)

        if best_first is None:
            return False, None, None, None

        _, first_name_tier, first_name_umlaut, middle_name_match = best_first

        return (
            True,
            first_name_tier,
            best_surname_umlaut or first_name_umlaut,
            middle_name_match,
        )

    if not candidate_pairs.empty:
        results = candidate_pairs.apply(verify, axis=1, result_type="expand")
        candidate_pairs[["is_match", "match_confidence", "umlaut_variant", "middle_name_match"]] = results
        confirmed = candidate_pairs[candidate_pairs["is_match"]].merge(
            researchers[["researcher_idx", "labgroupid"]], on="researcher_idx", how="left"
        )
        confirmed = confirmed[
            ["creator_key", "labgroupid", "match_confidence", "umlaut_variant", "middle_name_match"]
        ]
    else:
        confirmed = pd.DataFrame(
            columns=["creator_key", "labgroupid", "match_confidence", "umlaut_variant", "middle_name_match"]
        )

    # ---- Step 7: map confirmed matches back onto every publication row ----
    creators = creators.merge(confirmed, on="creator_key", how="left")

    # ---- Step 8: collapse back down to one row per publication -------------
    def aggregate(group):
        matched = group.dropna(subset=["labgroupid"]).copy()
        matched["labgroupid"] = matched["labgroupid"].astype(researchers_df["labgroupid"].dtype)

        # If the same labgroupid was reached via more than one creator/tier
        # on this publication, keep only the cleanest (best confidence,
        # fewest guesses) version of that match for reporting - preferring a
        # middle-name-confirmed match over an unconfirmed one as a tie-break.
        matched["_rank"] = list(zip(
            matched["match_confidence"].map(CONFIDENCE_RANK),
            matched["umlaut_variant"],
            matched["middle_name_match"].map(lambda x: not x),
        ))
        best = matched.sort_values("_rank").drop_duplicates(subset=["labgroupid"], keep="first")
        best = best.sort_values("labgroupid")

        return pd.Series({
            "matched_labgroupids": best["labgroupid"].tolist(),
            "match_confidence": best["match_confidence"].tolist(),
            "umlaut_variant": best["umlaut_variant"].tolist(),
            "middle_name_match": best["middle_name_match"].tolist(),
        })

    out = creators.groupby(id_col, sort=False).apply(aggregate).reset_index()

    return out
