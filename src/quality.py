from pathlib import Path
import pandas as pd


def compare_file_schemas(
    directory: Path, extension: str = ".xls", sep: str = "\t", encoding: str = "latin1"
) -> pd.DataFrame:
    """
    Compare the schema of all files in a directory.

    The first file is used as the reference schema.

    Parameters
    ----------
    directory : Path
        Directory containing the files.

    extension : str, default=".xls"
        File extension to inspect.

    sep : str, default="\\t"
        Column separator.

    encoding : str, default="latin1"
        File encoding.

    Returns
    -------
    pd.DataFrame
        Schema comparison report containing:
        - file name
        - number of columns
        - whether schema matches reference
        - missing columns
        - extra columns
        - columns with different dtypes
    """

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = sorted(directory.glob(f"*{extension}"))

    if not files:
        raise FileNotFoundError(f"No {extension} files found in {directory}")

    # --------------------------------------------------
    # 1. Read schemas
    # --------------------------------------------------

    schemas = {}

    for file_path in files:
        df = pd.read_csv(file_path, sep=sep, encoding=encoding)

        schemas[file_path.name] = {
            "columns": list(df.columns),
            "columns_set": set(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
        }

    # --------------------------------------------------
    # 2. Reference schema
    # --------------------------------------------------

    reference_file = files[0].name
    reference_schema = schemas[reference_file]

    reference_columns = reference_schema["columns"]
    reference_columns_set = reference_schema["columns_set"]
    reference_dtypes = reference_schema["dtypes"]

    # --------------------------------------------------
    # 3. Compare schemas
    # --------------------------------------------------

    report = []

    for filename, schema in schemas.items():
        current_columns = schema["columns"]
        current_columns_set = schema["columns_set"]
        current_dtypes = schema["dtypes"]

        missing_columns = sorted(reference_columns_set - current_columns_set)

        extra_columns = sorted(current_columns_set - reference_columns_set)

        # Compare order
        same_column_order = current_columns == reference_columns

        # Compare dtypes only for columns existing in both files
        common_columns = reference_columns_set & current_columns_set

        dtype_differences = {}

        for column in common_columns:
            reference_dtype = reference_dtypes[column]
            current_dtype = current_dtypes[column]

            if reference_dtype != current_dtype:
                dtype_differences[column] = {
                    "reference": reference_dtype,
                    "current": current_dtype,
                }

        same_columns = len(missing_columns) == 0 and len(extra_columns) == 0

        same_dtypes = len(dtype_differences) == 0

        same_schema = same_columns and same_dtypes and same_column_order

        report.append(
            {
                "file": filename,
                "n_columns": len(current_columns),
                "same_columns": same_columns,
                "same_column_order": same_column_order,
                "same_dtypes": same_dtypes,
                "same_schema": same_schema,
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
                "dtype_differences": dtype_differences,
            }
        )

    report_df = pd.DataFrame(report)

    # --------------------------------------------------
    # 4. Console summary
    # --------------------------------------------------

    print("=" * 80)
    print("SCHEMA VALIDATION REPORT")
    print("=" * 80)

    print(f"Reference file : {reference_file}")
    print(f"Reference columns : {len(reference_columns)}")

    print("-" * 80)

    for row in report:
        print(f"\nFile: {row['file']}")

        print(f"Columns          : {row['n_columns']}")

        print(f"Same columns     : {row['same_columns']}")

        print(f"Same order       : {row['same_column_order']}")

        print(f"Same dtypes      : {row['same_dtypes']}")

        print(f"Same schema      : {row['same_schema']}")

        if row["missing_columns"]:
            print("Missing columns   :", row["missing_columns"])

        if row["extra_columns"]:
            print("Extra columns     :", row["extra_columns"])

        if row["dtype_differences"]:
            print("Dtype differences :", row["dtype_differences"])

    return report_df


# ============================================================
# DATA QUALITY REPORT
# ============================================================


import pandas as pd


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rapport de qualité annuel comparatif par région.
    """

    data = df.assign(year=df["datetime"].dt.year).copy()

    # Agrégation par région et année
    report = (
        data.groupby(["Périmètre", "year"])
        .agg(
            rows=("datetime", "size"),
            datetime_missing=("datetime", lambda x: x.isna().sum()),
            datetime_unique=("datetime", "nunique"),
            datetime_min=("datetime", "min"),
            datetime_max=("datetime", "max"),
            consommation_missing=("Consommation", lambda x: x.isna().sum()),
            consommation_valid=("Consommation", "count"),
        )
        .reset_index()
    )

    # Indicateurs dérivés
    report["duplicate_datetime"] = report["rows"] - report["datetime_unique"]

    report["expected_rows"] = report["year"].apply(
        lambda year: (pd.Timestamp(year + 1, 1, 1) - pd.Timestamp(year, 1, 1)).days * 48
    )

    report["temporal_coverage_pct"] = (
        report["datetime_unique"] / report["expected_rows"] * 100
    ).round(2)

    report["consommation_missing_pct"] = (
        report["consommation_missing"] / report["rows"] * 100
    ).round(2)

    # Tableau comparatif
    report = report.pivot_table(
        index="year",
        columns="Périmètre",
        values=[
            "rows",
            "expected_rows",
            "datetime_missing",
            "datetime_unique",
            "duplicate_datetime",
            "temporal_coverage_pct",
            "consommation_missing",
            "consommation_missing_pct",
            "consommation_valid",
            "datetime_min",
            "datetime_max",
        ],
        aggfunc="first",
    )

    # Régions en premier niveau
    report = report.swaplevel(axis=1).sort_index(axis=1)

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
