"""
NeuroProgress - Step 1: Raw data audit.

Reads the raw ADNI longitudinal CSV and reports facts needed before any
cleaning decision is made: shape, duplicates, date validity, per-column
missingness, ST*-feature inventory, clinical-feature inventory, and label
distributions. Writes no transformed data - this script only observes and
reports. All later preprocessing decisions (Step 2 onward) should be based
on this report, not assumptions.
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


def main():
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

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
    if "RID" in df.columns and "EXAMDATE" in df.columns:
        key_dupes = df.duplicated(subset=["RID", "EXAMDATE"]).sum()
        log(f"- Duplicate (RID, EXAMDATE) pairs: {key_dupes:,}")
    if "RID" in df.columns and "VISCODE" in df.columns:
        key_dupes2 = df.duplicated(subset=["RID", "VISCODE"]).sum()
        log(f"- Duplicate (RID, VISCODE) pairs: {key_dupes2:,}")
    log("")

    # --- 4. Dates ------------------------------------------------------
    log("## 4. Dates")
    for col in DATE_COLS:
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], format="%d-%m-%Y", errors="coerce")
        n_missing = df[col].isna().sum()
        n_unparseable = parsed.isna().sum() - n_missing
        log(f"- `{col}`: {n_missing:,} missing, {n_unparseable:,} present-but-unparseable "
            f"(assuming DD-MM-YYYY), range [{parsed.min()} .. {parsed.max()}]")
    if "EXAMDATE" in df.columns and "VISDATE" in df.columns:
        exam = pd.to_datetime(df["EXAMDATE"], format="%d-%m-%Y", errors="coerce")
        visd = pd.to_datetime(df["VISDATE"], format="%d-%m-%Y", errors="coerce")
        both = exam.notna() & visd.notna()
        mismatch = (exam[both] != visd[both]).sum()
        log(f"- Rows where EXAMDATE != VISDATE (both present): {mismatch:,} / {both.sum():,}")
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
    for col in VISIT_COLS:
        if col in df.columns:
            log(f"- `{col}` unique values ({df[col].nunique(dropna=True)}): "
                f"{sorted(df[col].dropna().unique().tolist())[:20]}{' ...' if df[col].nunique(dropna=True) > 20 else ''}")
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
    for col in clinical_cols:
        miss = df[col].isna().mean()
        log(f"  - `{col}`: {miss:.1%} missing, dtype={df[col].dtype}")
    log("")

    # --- 8. Label / outcome columns ---------------------------------------
    log("## 8. Label and outcome-related columns")
    for col in LABEL_COLS:
        if col not in df.columns:
            log(f"- `{col}`: NOT PRESENT in file")
            continue
        miss = df[col].isna().mean()
        if df[col].nunique(dropna=True) <= 10:
            vc = df[col].value_counts(dropna=False).to_dict()
            log(f"- `{col}`: {miss:.1%} missing, value counts: {vc}")
        else:
            log(f"- `{col}`: {miss:.1%} missing, {df[col].nunique(dropna=True)} unique values")
    log("")

    # --- 9. Patient / visit summary --------------------------------------
    log("## 9. Patient / visit summary")
    if "RID" in df.columns:
        visits_per_patient = df.groupby("RID").size()
        log(f"- Unique patients (RID): {df['RID'].nunique():,}")
        log(f"- Visits per patient: min={visits_per_patient.min()}, "
            f"median={visits_per_patient.median()}, max={visits_per_patient.max()}")
        log(f"- Patients with only 1 visit: {(visits_per_patient == 1).sum():,}")
    log("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
