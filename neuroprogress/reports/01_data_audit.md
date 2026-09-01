# NeuroProgress - Data Audit Report

Source file: `ADNI_UCSFFSX7_Based_Future_Labeled_Dataset.csv`

## 1. Shape
- Rows: 12,494
- Columns: 236
- Blank/unnamed columns: ['Unnamed: 5']

## 2. Identifiers
- `RID`: 3,179 unique values, 0 missing
- `PTID`: 3,179 unique values, 0 missing
- RIDs mapping to more than one PTID: 0

## 3. Duplicates
- Fully duplicated rows: 0
- Duplicate (RID, EXAMDATE) pairs: 861
- Duplicate (RID, VISCODE) pairs: 988

## 4. Dates
- `EXAMDATE`: 0 missing, 0 present-but-unparseable (assuming DD-MM-YYYY), range [2005-08-26 00:00:00 .. 2026-03-11 00:00:00]
- `VISDATE`: 9,163 missing, 0 present-but-unparseable (assuming DD-MM-YYYY), range [2005-08-17 00:00:00 .. 2026-02-10 00:00:00]
- Rows where EXAMDATE != VISDATE (both present): 2,739 / 3,331
- Patients whose rows are NOT already in chronological EXAMDATE order: 0 / 3,179

## 5. Visit codes
- `VISCODE` unique values (30): ['4_init', '4_m12', '4_m24', '4_sc', 'bl', 'init', 'm03', 'm06', 'm12', 'm18', 'm24', 'm36', 'm48', 'm60', 'm72', 'sc', 'scmri', 'v02', 'v04', 'v05'] ...
- `VISCODE2` unique values (43): ['bl', 'm03', 'm06', 'm102', 'm108', 'm114', 'm12', 'm120', 'm126', 'm132', 'm138', 'm144', 'm150', 'm156', 'm162', 'm168', 'm174', 'm18', 'm180', 'm186'] ...

## 6. ST* brain feature columns
- ST* columns matching `ST<region>(CV|TA|SV)`: 186
- Columns starting with 'ST' but not matching the pattern: none
- ST* columns with >50% missingness: 1
  ST68SV (90.8%)
- ST* columns retained at <=50% missingness threshold: 185

## 7. Clinical / cognitive feature columns
- Candidate clinical columns (26): ['PTGENDER', 'PTEDUCAT', 'MMTRIALS', 'MMD', 'MML', 'MMR', 'MMO', 'MMW', 'MMWATCH', 'MMPENCIL', 'MMREPEAT', 'MMHAND', 'MMFOLD', 'MMONFLR', 'MMREAD', 'MMWRITE', 'MMDRAW', 'MMSCORE', 'CDMEMORY', 'CDORIENT', 'CDJUDGE', 'CDCOMMUN', 'CDHOME', 'CDCARE', 'CDGLOBAL', 'CDRSB']
  - `PTGENDER`: 74.0% missing, dtype=float64
  - `PTEDUCAT`: 74.0% missing, dtype=float64
  - `MMTRIALS`: 42.6% missing, dtype=float64
  - `MMD`: 42.7% missing, dtype=float64
  - `MML`: 42.7% missing, dtype=float64
  - `MMR`: 42.7% missing, dtype=float64
  - `MMO`: 42.7% missing, dtype=float64
  - `MMW`: 42.7% missing, dtype=float64
  - `MMWATCH`: 15.1% missing, dtype=float64
  - `MMPENCIL`: 15.1% missing, dtype=float64
  - `MMREPEAT`: 15.1% missing, dtype=float64
  - `MMHAND`: 15.1% missing, dtype=float64
  - `MMFOLD`: 15.1% missing, dtype=float64
  - `MMONFLR`: 15.1% missing, dtype=float64
  - `MMREAD`: 15.1% missing, dtype=float64
  - `MMWRITE`: 15.1% missing, dtype=float64
  - `MMDRAW`: 15.1% missing, dtype=float64
  - `MMSCORE`: 15.1% missing, dtype=float64
  - `CDMEMORY`: 15.1% missing, dtype=float64
  - `CDORIENT`: 15.1% missing, dtype=float64
  - `CDJUDGE`: 15.1% missing, dtype=float64
  - `CDCOMMUN`: 15.1% missing, dtype=float64
  - `CDHOME`: 15.1% missing, dtype=float64
  - `CDCARE`: 15.1% missing, dtype=float64
  - `CDGLOBAL`: 15.1% missing, dtype=float64
  - `CDRSB`: 15.6% missing, dtype=float64

## 8. Label and outcome-related columns
- `DXAD`: 0.0% missing, value counts: {0: 9286, -4: 2248, 1: 960}
- `FIRST_AD_DATE`: 85.1% missing, 276 unique values
- `DAYS_TO_FIRST_AD`: 85.1% missing, 689 unique values
- `DIAGNOSIS`: 22.2% missing, value counts: {2.0: 3945, 1.0: 3800, nan: 2768, 3.0: 1981}
- `DXNORM`: 74.3% missing, value counts: {nan: 9286, -4.0: 2216, 1.0: 992}
- `DXMCI`: 74.3% missing, value counts: {nan: 9286, -4.0: 1957, 1.0: 1251}
- `ALZHEIMER_LABEL`: 74.3% missing, value counts: {nan: 9286, 0.0: 2248, 1.0: 960}
- `FUTURE_ALZHEIMER`: 0.0% missing, value counts: {0: 11744, 1: 750}
- `FUTURE_ALZHEIMER_LABEL`: 0.0% missing, value counts: {0: 11744, 1: 750}

## 9. Patient / visit summary
- Unique patients (RID): 3,179
- Visits per patient: min=1, median=3.0, max=20
- Patients with only 1 visit: 953

## 10. Additional checks
- `FUTURE_ALZHEIMER` and `FUTURE_ALZHEIMER_LABEL` are identical on every row (redundant columns; keep one as the target, drop the other).
- `DXAD` vs `DIAGNOSIS` cross-tab:

  | DXAD \\ DIAGNOSIS | 1 (CN) | 2 (MCI) | 3 (AD) | NaN |
  |---|---|---|---|---|
  | -4 | 992 | 1254 | 2 | 0 |
  | 0 | 2808 | 2691 | 1019 | 2768 |
  | 1 | 0 | 0 | 960 | 0 |

  `DXAD=1` lines up exactly with `DIAGNOSIS=3` (current-visit AD) in 960 rows, so `DXAD=1` looks like "diagnosed AD at this visit." `DXAD=-4` looks like a sentinel ("not applicable"/not tracked) rather than a real 0/1 value, and it does not cleanly separate by `DIAGNOSIS`. **Do not guess further** - the exact coding of `DXAD`, `DXNORM`, `DXMCI`, `ALZHEIMER_LABEL`, `-4` sentinels, and how `FUTURE_ALZHEIMER` / `FUTURE_ALZHEIMER_LABEL` were actually derived (window logic, censoring rule) needs to be confirmed against the ADNI data dictionary / whatever script produced this "Future_Labeled" file, before it is trusted as the modeling target.

## 11. Flags to resolve before Step 2 (cleaning)

1. **Unnamed: 5** - a stray blank column from the source export. Drop it.
2. **861 duplicate (RID, EXAMDATE) pairs / 988 duplicate (RID, VISCODE) pairs** - not full row duplicates, so these are either genuinely repeated exams or multiple source tables merged per visit. Needs a dedup rule, not a blind `drop_duplicates()`.
3. **VISDATE is 73% missing**; where both `EXAMDATE` and `VISDATE` are present they disagree 82% of the time (2,739/3,331). Recommend treating `EXAMDATE` as the canonical visit date and dropping/ignoring `VISDATE`, but this should be a deliberate decision, not a default.
4. **VISCODE has 30 distinct codes, VISCODE2 has 43** (including phase-prefixed codes like `4_init`, `4_sc`, `4_m12`), reflecting ADNI1/GO/2/3 phase changes. These need to be harmonized into a single visit-order scheme before building per-patient sequences, since the same relative timepoint is coded differently across phases.
5. **`ST68SV`** is the one ST* column over the 50% missingness threshold (90.8% missing) - confirms the 186 -> 185 drop.
6. **`PTGENDER` / `PTEDUCAT` are 74% missing** despite being static demographics - almost certainly only populated on one row per patient (e.g. baseline) in this export and need to be forward/backward-filled per RID rather than treated as missing-at-random.
7. **`FIRST_AD_DATE` / `DAYS_TO_FIRST_AD`** are present on 14.9% of rows and are explicitly future-derived (used to build the label). These must be excluded from model input features entirely (Section 24 of the spec) - keep them only in the label-construction step, never in the feature matrix.
8. **953 / 3,179 patients (30%) have only 1 visit.** Since NeuroProgress needs longitudinal history (>=2 visits to compute deltas/rates), single-visit patients cannot be used for the longitudinal models (Models 2-4) and need an explicit inclusion/exclusion decision - likely usable only for Model 1 (Clinical MLP, cross-sectional).
