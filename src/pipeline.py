from pathlib import Path
import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_PATH = Path(r"C:\Full_stack\Portfolios\Projets\Data_Analysis_Projects\rte")

RAW_DATA_PATH = PROJECT_PATH / "data" / "raw" / "dezip_file"
PROCESSED_DATA_PATH = PROJECT_PATH / "data" / "processed"

PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================
# COLUMNS
# ============================================================

CORE_COLUMNS = [
    "Date",
    "Heures",
    "Consommation",
    "Thermique",
    "Nucléaire",
    "Eolien",
    "Solaire",
    "Hydraulique",
    "Pompage",
    "Bioénergies",
    "Ech. physiques",
]


EXTENDED_COLUMNS = CORE_COLUMNS + [
    "Stockage batterie",
    "Déstockage batterie",
    "Eolien terrestre",
    "Eolien offshore",
]


NUMERIC_COLUMNS = [
    "Consommation",
    "Thermique",
    "Nucléaire",
    "Eolien",
    "Solaire",
    "Hydraulique",
    "Pompage",
    "Bioénergies",
    "Ech. physiques",
    "Stockage batterie",
    "Déstockage batterie",
    "Eolien terrestre",
    "Eolien offshore",
]


# ============================================================
# METADATA EXTRACTION
# ============================================================


def extract_year(filename: str) -> int:
    """
    Extract year from RTE filename.
    """

    match = re.search(r"(20\d{2})", filename)

    if match is None:
        raise ValueError(f"Unable to extract year from filename: {filename}")

    return int(match.group(1))


def extract_region(filename: str) -> str:
    """
    Extract region name from RTE filename.
    """

    pattern = r"eCO2mix_RTE_(.+?)_Annuel-Definitif"

    match = re.search(pattern, filename)

    if match is None:
        raise ValueError(f"Unable to extract region from filename: {filename}")

    return match.group(1)


# ============================================================
# LOAD RAW FILE
# ============================================================


def load_raw_file(
    file_path: Path, sep: str = "\t", encoding: str = "latin1"
) -> pd.DataFrame:
    """
    Load one raw RTE file.

    Data is initially loaded as string to prevent
    pandas from inferring inconsistent dtypes.
    """

    df = pd.read_csv(file_path, sep=sep, encoding=encoding, dtype=str, low_memory=False)

    return df


# ============================================================
# REMOVE TECHNICAL / EMPTY COLUMNS
# ============================================================


def remove_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove columns generated without meaningful names.
    """

    mask = ~df.columns.str.startswith("Unnamed")

    return df.loc[:, mask].copy()


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize leading/trailing spaces in column names.
    """

    df = df.copy()

    df.columns = df.columns.str.strip()

    return df


# ============================================================
# REMOVE EMPTY ROWS
# ============================================================


def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove completely empty rows and footer rows
    without Date / Heures.
    """

    df = df.dropna(how="all")

    if {"Date", "Heures"}.issubset(df.columns):
        df = df.dropna(subset=["Date", "Heures"], how="all")

    return df.copy()


# ============================================================
# NUMERIC CONVERSION
# ============================================================


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert known energy variables to numeric.
    Invalid values become NaN.
    """

    df = df.copy()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column].str.replace(",", ".", regex=False).str.strip(),
                errors="coerce",
            )

    return df


# ============================================================
# DATETIME
# ============================================================


def create_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine Date and Heures into one datetime column.
    """

    df = df.copy()

    df["datetime"] = pd.to_datetime(
        df["Date"].astype(str).str.strip() + " " + df["Heures"].astype(str).str.strip(),
        errors="coerce",
        dayfirst=True,
    )

    return df


# ============================================================
# NORMALIZE SCHEMA
# ============================================================


def normalize_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Guarantee that every requested column exists.

    Missing columns are created with NA.
    """

    df = df.copy()

    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA

    return df


# ============================================================
# DETECT FLOW COLUMNS
# ============================================================


def get_flow_columns(df: pd.DataFrame) -> list[str]:
    """
    Return detailed physical flow columns.
    """

    return [column for column in df.columns if column.startswith("Flux physiques")]


# ============================================================
# TRANSFORM FLOWS TO LONG FORMAT
# ============================================================


def reshape_flows(df: pd.DataFrame, region: str, year: int) -> pd.DataFrame:
    """
    Convert wide RTE physical flow variables to long format.
    """

    flow_columns = get_flow_columns(df)

    if not flow_columns:
        return pd.DataFrame(
            columns=["datetime", "region", "year", "flow_name", "flow_mw"]
        )

    flows = df[["datetime"] + flow_columns].copy()

    flows = flows.melt(
        id_vars=["datetime"],
        value_vars=flow_columns,
        var_name="flow_name",
        value_name="flow_mw",
    )

    flows["flow_mw"] = pd.to_numeric(flows["flow_mw"], errors="coerce")

    flows["region"] = region
    flows["year"] = year

    flows = flows[["datetime", "region", "year", "flow_name", "flow_mw"]]

    return flows


# ============================================================
# PROCESS ONE FILE
# ============================================================


def process_rte_file(
    file_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Process one RTE file and return:

    - core dataset
    - extended dataset
    - physical flows dataset
    """

    filename = file_path.name

    region = extract_region(filename)
    year = extract_year(filename)

    print(f"Processing: {region} - {year}")

    # ----------------------------
    # Load
    # ----------------------------

    df = load_raw_file(file_path)

    # ----------------------------
    # Basic cleaning
    # ----------------------------

    df = clean_column_names(df)

    df = remove_unnamed_columns(df)

    df = remove_empty_rows(df)

    # ----------------------------
    # Metadata
    # ----------------------------

    df["region"] = region
    df["year"] = year
    df["source_file"] = filename

    # ----------------------------
    # Datetime
    # ----------------------------

    df = create_datetime(df)

    # ----------------------------
    # Numeric conversion
    # ----------------------------

    df = convert_numeric_columns(df)

    # ========================================================
    # FLOWS
    # ========================================================

    flows_df = reshape_flows(df=df, region=region, year=year)

    # ========================================================
    # CORE DATASET
    # ========================================================

    df = normalize_columns(df, CORE_COLUMNS)

    core_df = df[
        [
            "datetime",
            "region",
            "year",
            "source_file",
        ]
        + [column for column in CORE_COLUMNS if column not in ["Date", "Heures"]]
    ].copy()

    # ========================================================
    # EXTENDED DATASET
    # ========================================================

    df = normalize_columns(df, EXTENDED_COLUMNS)

    extended_df = df[
        [
            "datetime",
            "region",
            "year",
            "source_file",
        ]
        + [column for column in EXTENDED_COLUMNS if column not in ["Date", "Heures"]]
    ].copy()

    return (core_df, extended_df, flows_df)


# ============================================================
# DATA QUALITY REPORT
# ============================================================


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a data quality summary by region and year.
    """

    report = (
        df.groupby(["region", "year"], dropna=False)
        .agg(
            rows=("datetime", "size"),
            datetime_missing=("datetime", lambda x: x.isna().sum()),
            datetime_unique=("datetime", "nunique"),
            datetime_min=("datetime", "min"),
            datetime_max=("datetime", "max"),
        )
        .reset_index()
    )

    report["duplicate_datetime"] = report["rows"] - report["datetime_unique"]

    return report


# ============================================================
# DUPLICATE VALIDATION
# ============================================================


def validate_primary_key(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect duplicate region + datetime observations.
    """

    duplicates = df[
        df.duplicated(subset=["datetime", "region"], keep=False)
    ].sort_values(["region", "datetime"])

    return duplicates


# ============================================================
# MAIN PIPELINE
# ============================================================


def run_pipeline(
    raw_path: Path, processed_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run complete RTE preparation pipeline.
    """

    files = sorted(raw_path.glob("*.xls"))

    if not files:
        raise FileNotFoundError(f"No .xls files found in {raw_path}")

    core_dfs = []
    extended_dfs = []
    flows_dfs = []

    print("=" * 70)
    print("RTE DATA PREPARATION PIPELINE")
    print("=" * 70)

    print(f"Files found: {len(files)}")

    print("-" * 70)

    for file_path in files:
        try:
            (core_df, extended_df, flows_df) = process_rte_file(file_path)

            core_dfs.append(core_df)

            extended_dfs.append(extended_df)

            if not flows_df.empty:
                flows_dfs.append(flows_df)

        except Exception as error:
            print(f"ERROR | {file_path.name}")

            print(f"       {error}")

    # ========================================================
    # CONCAT
    # ========================================================

    core = pd.concat(core_dfs, ignore_index=True)

    extended = pd.concat(extended_dfs, ignore_index=True)

    if flows_dfs:
        flows = pd.concat(flows_dfs, ignore_index=True)

    else:
        flows = pd.DataFrame()

    # ========================================================
    # SORT
    # ========================================================

    core = core.sort_values(["region", "datetime"]).reset_index(drop=True)

    extended = extended.sort_values(["region", "datetime"]).reset_index(drop=True)

    # ========================================================
    # QUALITY
    # ========================================================

    quality_report = build_quality_report(core)

    duplicates = validate_primary_key(core)

    # ========================================================
    # SAVE
    # ========================================================

    core.to_parquet(processed_path / "rte_core_2013_2024.parquet", index=False)

    extended.to_parquet(processed_path / "rte_extended_2013_2024.parquet", index=False)

    if not flows.empty:
        flows.to_parquet(processed_path / "rte_physical_flows.parquet", index=False)

    quality_report.to_csv(processed_path / "quality_report.csv", index=False)

    if not duplicates.empty:
        duplicates.to_csv(processed_path / "duplicate_datetime_region.csv", index=False)

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)

    print(f"Core rows       : {len(core):,}")

    print(f"Core columns    : {core.shape[1]}")

    print(f"Extended rows   : {len(extended):,}")

    print(f"Extended cols   : {extended.shape[1]}")

    print(f"Flow rows       : {len(flows):,}")

    print(f"Duplicate PK    : {len(duplicates):,}")

    print()

    print(f"Regions:")

    print(core["region"].value_counts())

    return (core, extended, flows, quality_report)
