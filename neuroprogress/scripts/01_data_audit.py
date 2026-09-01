"""
NeuroProgress - Step 1: Raw data audit.

Reads the raw ADNI longitudinal CSV and reports facts needed before any
cleaning decision is made: shape, duplicates, date validity, per-column
missingness, ST*-feature inventory, clinical-feature inventory, and label
distributions. Writes no transformed data - this script only observes and
reports. All later preprocessing decisions (Step 2 onward) should be based
on this report, not assumptions. The full report, including the "Additional
checks" and "Flags to resolve" sections, is generated from the data below
so that rerunning this script always reproduces `reports/01_data_audit.md`.
"""
import re
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "ADNI_UCSFFSX7_Based_Future_Labeled_Dataset.csv"
REPORT_PATH = Path(__file__).resolve().parents[1] / "reports" / "01_data_audit.md"

ST_PATTERN = re.compile(r"^ST\d+(CV|TA|SV)$")
ID_COLS = ["RID", "PTID"]
DATE_COLS = ["EXAMDATE", "VISDATE"]
VISIT_COLS = ["VISCODE", "VISCODE2"]
LABEL_COLS = [
    "DXAD", "FIRST_AD_DATE", "DAYS_TO_FIRST_AD",
    "DIAGNOSIS", "DXNORM", "DXMCI", "ALZHEIMER_LABEL",
    "FUTURE_ALZHEIMER", "FUTURE_ALZHEIMER_LABEL",
]
CLINICAL_PREFIXES = ("PTGENDER", "PTEDUCAT", "MM", "CD")
PHASE_PREFIXED_VISCODE = re.compile(r"^\d+_")


def main():
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_PATH}. It is gitignored/restricted data - "
            "place the ADNI CSV there before running this script."
        )
    df = pd.read_csv(RAW_PATH, low_memory=False)

    log("# NeuroProgress - Data Audit Report\n")
    log(f"Source file: `{RAW_PATH.name}`\n")

    # --- 1. Shape and unnamed columns -----------------------------------
    log("## 1. Shape")
    log(f"- Rows: {len(df):,}")
    log(f"- Columns: {df.shape[1]:,}")
    unnamed = [c for c in df.columns if str(c).strip() == "" or str(c).startswith("Unnamed")]
    log(f"- Blank/unnamed columns: {unnamed if unnamed else 'none'}")
    log("")

    # --- 2. Identifier columns -------------------------------------------
    log("## 2. Identifiers")
    for col in ID_COLS:
        if col in df.columns:
            n_unique = df[col].nunique(dropna=True)
            n_missing = df[col].isna().sum()
            log(f"- `{col}`: {n_unique:,} unique values, {n_missing:,} missing")
    if "RID" in df.columns and "PTID" in df.columns:
        rid_to_ptid = df.groupby("RID")["PTID"].nunique()
        inconsistent = rid_to_ptid[rid_to_ptid > 1]
        log(f"- RIDs mapping to more than one PTID: {len(inconsistent)}")
    log("")

    # --- 3. Duplicates -----------------------------------------------------
    log("## 3. Duplicates")
    full_dupes = df.duplicated().sum()
    log(f"- Fully duplicated rows: {full_dupes:,}")
    key_dupes = key_dupes2 = None
    if "RID" in df.columns and "EXAMDATE" in df.columns:
        key_dupes = int(df.duplicated(subset=["RID", "EXAMDATE"]).sum())
        log(f"- Duplicate (RID, EXAMDATE) pairs: {key_dupes:,}")
    if "RID" in df.columns and "VISCODE" in df.columns:
        key_dupes2 = int(df.duplicated(subset=["RID", "VISCODE"]).sum())
        log(f"- Duplicate (RID, VISCODE) pairs: {key_dupes2:,}")
    log("")

    # --- 4. Dates ------------------------------------------------------
    log("## 4. Dates")
    visdate_missing = visdate_mismatch = visdate_both = None
    for col in DATE_COLS:
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], format="%d-%m-%Y", errors="coerce")
        n_missing = df[col].isna().sum()
        n_unparseable = parsed.isna().sum() - n_missing
        log(f"- `{col}`: {n_missing:,} missing, {n_unparseable:,} present-but-unparseable "
            f"(assuming DD-MM-YYYY), range [{parsed.min()} .. {parsed.max()}]")
        if col == "VISDATE":
            visdate_missing = n_missing
    if "EXAMDATE" in df.columns and "VISDATE" in df.columns:
        exam = pd.to_datetime(df["EXAMDATE"], format="%d-%m-%Y", errors="coerce")
        visd = pd.to_datetime(df["VISDATE"], format="%d-%m-%Y", errors="coerce")
        both = exam.notna() & visd.notna()
        visdate_mismatch = int((exam[both] != visd[both]).sum())
        visdate_both = int(both.sum())
        log(f"- Rows where EXAMDATE != VISDATE (both present): {visdate_mismatch:,} / {visdate_both:,}")
    # chronological order per patient
    if "RID" in df.columns and "EXAMDATE" in df.columns:
        tmp = df[["RID", "EXAMDATE"]].copy()
        tmp["EXAMDATE"] = pd.to_datetime(tmp["EXAMDATE"], format="%d-%m-%Y", errors="coerce")
        tmp = tmp.dropna(subset=["EXAMDATE"])
        is_sorted_per_patient = tmp.groupby("RID")["EXAMDATE"].apply(lambda s: s.is_monotonic_increasing)
        n_unsorted = (~is_sorted_per_patient).sum()
        log(f"- Patients whose rows are NOT already in chronological EXAMDATE order: {n_unsorted:,} / {is_sorted_per_patient.shape[0]:,}")
    log("")

    # --- 5. Visit codes --------------------------------------------------
    log("## 5. Visit codes")
    viscode_n = viscode2_n = None
    phase_prefixed_codes = []
    for col in VISIT_COLS:
        if col in df.columns:
            n_unique = df[col].nunique(dropna=True)
            uniq_sorted = sorted(df[col].dropna().unique().tolist())
            log(f"- `{col}` unique values ({n_unique}): "
                f"{uniq_sorted[:20]}{' ...' if n_unique > 20 else ''}")
            if col == "VISCODE":
                viscode_n = n_unique
            else:
                viscode2_n = n_unique
            phase_prefixed_codes += [c for c in uniq_sorted if PHASE_PREFIXED_VISCODE.match(str(c))]
    phase_prefixed_codes = sorted(set(phase_prefixed_codes))
    log("")

    # --- 6. ST* brain feature inventory ----------------------------------
    log("## 6. ST* brain feature columns")
    st_cols = [c for c in df.columns if ST_PATTERN.match(str(c))]
    log(f"- ST* columns matching `ST<region>(CV|TA|SV)`: {len(st_cols):,}")
    non_matching_st = [c for c in df.columns if str(c).startswith("ST") and not ST_PATTERN.match(str(c))]
    log(f"- Columns starting with 'ST' but not matching the pattern: {non_matching_st if non_matching_st else 'none'}")
    missing_frac = df[st_cols].isna().mean().sort_values(ascending=False)
    over_50 = missing_frac[missing_frac > 0.5]
    log(f"- ST* columns with >50% missingness: {len(over_50):,}")
    if len(over_50):
        log("  " + ", ".join(f"{c} ({v:.1%})" for c, v in over_50.items()))
    log(f"- ST* columns retained at <=50% missingness threshold: {len(st_cols) - len(over_50):,}")
    log("")

    # --- 7. Clinical feature inventory -----------------------------------
    log("## 7. Clinical / cognitive feature columns")
    clinical_cols = [c for c in df.columns if str(c).startswith(CLINICAL_PREFIXES)]
    log(f"- Candidate clinical columns ({len(clinical_cols)}): {clinical_cols}")
    clinical_missing = {}
    for col in clinical_cols:
        miss = df[col].isna().mean()
        clinical_missing[col] = miss
        log(f"  - `{col}`: {miss:.1%} missing, dtype={df[col].dtype}")
    log("")

    # --- 8. Label / outcome columns ---------------------------------------
    log("## 8. Label and outcome-related columns")
    label_missing = {}
    for col in LABEL_COLS:
        if col not in df.columns:
            log(f"- `{col}`: NOT PRESENT in file")
            continue
        miss = df[col].isna().mean()
        label_missing[col] = miss
        if df[col].nunique(dropna=True) <= 10:
            vc = df[col].value_counts(dropna=False).to_dict()
            log(f"- `{col}`: {miss:.1%} missing, value counts: {vc}")
        else:
            log(f"- `{col}`: {miss:.1%} missing, {df[col].nunique(dropna=True)} unique values")
    log("")

    # --- 9. Patient / visit summary --------------------------------------
    log("## 9. Patient / visit summary")
    n_patients = single_visit_patients = None
    if "RID" in df.columns:
        visits_per_patient = df.groupby("RID").size()
        n_patients = df["RID"].nunique()
        single_visit_patients = int((visits_per_patient == 1).sum())
        log(f"- Unique patients (RID): {n_patients:,}")
        log(f"- Visits per patient: min={visits_per_patient.min()}, "
            f"median={visits_per_patient.median()}, max={visits_per_patient.max()}")
        log(f"- Patients with only 1 visit: {single_visit_patients:,}")
    log("")

    # --- 10. Additional checks --------------------------------------------
    log("## 10. Additional checks")
    if "FUTURE_ALZHEIMER" in df.columns and "FUTURE_ALZHEIMER_LABEL" in df.columns:
        identical = (df["FUTURE_ALZHEIMER"] == df["FUTURE_ALZHEIMER_LABEL"]).all()
        log(f"- `FUTURE_ALZHEIMER` and `FUTURE_ALZHEIMER_LABEL` identical on every row: {identical} "
            f"({'redundant columns; keep one as the target, drop the other' if identical else 'DIFFER - investigate before using either as the target'})")
    if "DXAD" in df.columns and "DIAGNOSIS" in df.columns:
        crosstab = pd.crosstab(df["DXAD"], df["DIAGNOSIS"], dropna=False)
        log("- `DXAD` vs `DIAGNOSIS` cross-tab:")
        log("")
        log("  ```")
        for line in crosstab.to_string().splitlines():
            log(f"  {line}")
        log("  ```")
        log("")
        log("  Do not guess further - the exact coding of `DXAD`, `DXNORM`, `DXMCI`, `ALZHEIMER_LABEL`, "
            "`-4` sentinels, and how `FUTURE_ALZHEIMER` / `FUTURE_ALZHEIMER_LABEL` were actually derived "
            "(window logic, censoring rule) needs to be confirmed against the ADNI data dictionary / "
            "whatever script produced this \"Future_Labeled\" file, before it is trusted as the modeling target.")
    log("")

    # --- 11. Flags to resolve before Step 2 --------------------------------
    log("## 11. Flags to resolve before Step 2 (cleaning)")
    flag_n = 1

    def flag(text):
        nonlocal flag_n
        log(f"{flag_n}. {text}")
        flag_n += 1

    if unnamed:
        cols_text = ", ".join(f"`{c}`" for c in unnamed)
        flag(f"**{cols_text}** - stray blank column(s) from the source export. Drop {'them' if len(unnamed) > 1 else 'it'}.")
    if key_dupes is not None and key_dupes2 is not None:
        flag(f"**{key_dupes:,} duplicate (RID, EXAMDATE) pairs / {key_dupes2:,} duplicate (RID, VISCODE) pairs** - "
             "not full row duplicates, so these are either genuinely repeated exams or multiple source tables "
             "merged per visit. Needs a dedup rule, not a blind `drop_duplicates()`.")
    if visdate_missing is not None and visdate_mismatch is not None and visdate_both:
        flag(f"**VISDATE is {visdate_missing / len(df):.0%} missing**; where both `EXAMDATE` and `VISDATE` are "
             f"present they disagree {visdate_mismatch / visdate_both:.0%} of the time "
             f"({visdate_mismatch:,}/{visdate_both:,}). Recommend treating `EXAMDATE` as the canonical visit date "
             "and dropping/ignoring `VISDATE`, but this should be a deliberate decision, not a default.")
    if viscode_n is not None and viscode2_n is not None:
        flag(f"**VISCODE has {viscode_n} distinct codes, VISCODE2 has {viscode2_n}** (including phase-prefixed "
             f"codes like {phase_prefixed_codes[:5]}{' ...' if len(phase_prefixed_codes) > 5 else ''}), reflecting "
             "ADNI1/GO/2/3 phase changes. These need to be harmonized into a single visit-order scheme before "
             "building per-patient sequences, since the same relative timepoint is coded differently across phases.")
    if len(over_50):
        flag(f"**`{', '.join(over_50.index)}`** is the ST* column over the 50% missingness threshold "
             f"({over_50.iloc[0]:.1%} missing) - confirms the {len(st_cols)} -> {len(st_cols) - len(over_50)} drop.")
    for demo_col in ("PTGENDER", "PTEDUCAT"):
        if demo_col in clinical_missing and clinical_missing[demo_col] > 0.5:
            flag(f"**`{demo_col}` is {clinical_missing[demo_col]:.0%} missing** despite being a static "
                 "demographic - almost certainly only populated on one row per patient (e.g. baseline) in this "
                 "export and needs to be forward/backward-filled per RID rather than treated as missing-at-random.")
            break
    if "FIRST_AD_DATE" in label_missing:
        flag(f"**`FIRST_AD_DATE` / `DAYS_TO_FIRST_AD`** are present on {1 - label_missing['FIRST_AD_DATE']:.1%} of "
             "rows and are explicitly future-derived (used to build the label). These must be excluded from model "
             "input features entirely (Section 24 of the spec) - keep them only in the label-construction step, "
             "never in the feature matrix.")
    if n_patients and single_visit_patients is not None:
        flag(f"**{single_visit_patients:,} / {n_patients:,} patients ({single_visit_patients / n_patients:.0%}) have "
             "only 1 visit.** Since NeuroProgress needs longitudinal history (>=2 visits to compute deltas/rates), "
             "single-visit patients cannot be used for the longitudinal models (Models 2-4) and need an explicit "
             "inclusion/exclusion decision - likely usable only for Model 1 (Clinical MLP, cross-sectional).")
    log("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
