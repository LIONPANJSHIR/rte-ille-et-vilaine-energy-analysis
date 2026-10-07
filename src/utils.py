from pathlib import Path
import pandas as pd


def summarize_directory(directory: Path) -> dict:
    """
    Display a summary of files contained in a directory.

    Parameters
    ----------
    directory : Path
        Directory to inspect.

    Returns
    -------
    dict
        Summary containing the number of files
        and the total directory size in MB.
    """

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    file_count = 0
    total_size_bytes = 0

    print(f"\nDirectory: {directory.resolve()}")
    print("-" * 70)

    for file_path in sorted(directory.iterdir()):
        if not file_path.is_file():
            continue

        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / 1_000_000

        print(f"{file_path.name:<55}{size_mb:>10.2f} MB")

        file_count += 1
        total_size_bytes += size_bytes

    total_size_mb = total_size_bytes / 1_000_000
    total_size_gb = total_size_bytes / 1_000_000_000

    print("-" * 70)
    print(f"{'File count':<20}: {file_count}")
    print(f"{'Total size':<20}: {total_size_mb:.2f} MB")
    print(f"{'Total size':<20}: {total_size_gb:.3f} GB")

    return {
        "file_count": file_count,
        "total_size_mb": total_size_mb,
        "total_size_gb": total_size_gb,
    }


def inspect_data_files(
    directory: Path, extension: str = ".xls", n_head: int = 5
) -> dict:
    """
    Inspect all data files in a directory.

    Parameters
    ----------
    directory : Path
        Directory containing the data files.

    extension : str, default=".xls"
        File extension to inspect.

    n_head : int, default=5
        Number of rows to display in the preview.

    Returns
    -------
    dict
        Dictionary containing metadata and structural information
        for each file.
    """

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    results = {}

    files = sorted(directory.glob(f"*{extension}"))

    if not files:
        print(f"No {extension} files found in {directory}")
        return results

    for file_path in files:
        print("\n" + "=" * 80)
        print(f"FILE: {file_path.name}")
        print("=" * 80)

        # À adapter selon ton format RTE
        df = pd.read_csv(file_path, sep="\t", encoding="latin1")

        file_info = {
            "rows": df.shape[0],
            "columns_count": df.shape[1],
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "memory_mb": df.memory_usage(deep=True).sum() / 1_000_000,
            "missing_values": df.isna().sum().to_dict(),
            "duplicate_rows": df.duplicated().sum(),
            "head": df.head(n_head),
        }

        results[file_path.name] = file_info

        print(f"Rows           : {file_info['rows']:,}")
        print(f"Columns        : {file_info['columns_count']}")
        print(f"Memory usage   : {file_info['memory_mb']:.2f} MB")
        print(f"Duplicate rows : {file_info['duplicate_rows']:,}")

        print("\nColumns:")
        print(df.columns.tolist())

        print("\nData types:")
        print(df.dtypes)

        print("\nMissing values:")
        print(df.isna().sum())

        print("\nDataFrame structure:")
        df.info()

        print(f"\nHead ({n_head} rows):")
        print(df.head(n_head))

    return results
