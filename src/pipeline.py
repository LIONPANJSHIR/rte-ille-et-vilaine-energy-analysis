"""Pipeline ETL RTE eCO2mix : Bretagne et Auvergne-Rhône-Alpes (2013–2024)."""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests


# Configuration — chemins d'origine
PROJECT_DIR = Path(r"C:\Full_stack\Portfolios\Projets\Data_Analysis_Projects\rte")
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "rte_comparison_2013_2024.parquet"
BASE_URL = "https://eco2mix.rte-france.com/download/eco2mix"

REGION_SLUGS = {
    "Auvergne-Rhône-Alpes": "Auvergne-Rh%C3%B4ne-Alpes",
    "Bretagne": "Bretagne",
}
YEARS = range(2013, 2025)

COLUMNS_ANALYSIS = [
    "Périmètre",
    "datetime",
    "Consommation",
    "Nucléaire",
    "Thermique",
    "Eolien",
    "Solaire",
    "Hydraulique",
    "Pompage",
    "Bioénergies",
    "Ech. physiques",
    "Eolien terrestre",
    "Eolien offshore",
]
NA_VALUES = ["-", "", "NA", "N/A", "ND"]


def download_data_zip(force: bool = False) -> None:
    """Télécharge les archives manquantes ou toutes les archives si force=True."""
    for region, slug in REGION_SLUGS.items():
        region_dir = RAW_DIR / region
        region_dir.mkdir(parents=True, exist_ok=True)

        for year in YEARS:
            stem = f"eCO2mix_RTE_{region}_Annuel-Definitif_{year}"
            xls_path = region_dir / f"{stem}.xls"
            zip_path = region_dir / f"{stem}.zip"

            if not force and (xls_path.exists() or zip_path.exists()):
                continue

            url = f"{BASE_URL}/eCO2mix_RTE_{slug}_Annuel-Definitif_{year}.zip"
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            print(f"DOWNLOAD | {region} - {year}")


def extract_files(delete_zip: bool = True) -> None:
    """Extrait les archives téléchargées puis supprime les ZIP."""
    for region in REGION_SLUGS:
        region_dir = RAW_DIR / region
        for zip_path in sorted(region_dir.glob("*.zip")):
            with ZipFile(zip_path) as archive:
                archive.extractall(region_dir)
            if delete_zip:
                zip_path.unlink()
            print(f"EXTRACT  | {zip_path.name}")


def load_data_rte(raw_dir: str | Path = RAW_DIR) -> pd.DataFrame:
    """Charge, nettoie et concatène les fichiers régionaux annuels."""
    raw_dir = Path(raw_dir)
    all_data = []
    numeric_vars = [
        col for col in COLUMNS_ANALYSIS if col not in ["Périmètre", "datetime"]
    ]

    for region in REGION_SLUGS:
        region_dir = raw_dir / region
        for file in sorted(region_dir.glob("*.xls")):
            df = pd.read_csv(
                file,
                sep="\t",
                encoding="latin1",
                dtype=str,
                na_values=NA_VALUES,
                keep_default_na=True,
                index_col=False,
            )

            df.columns = df.columns.str.strip()
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")].copy()
            df = df.loc[:, ~df.columns.str.startswith("Flux physiques")].copy()

            df["datetime"] = pd.to_datetime(
                df["Date"] + " " + df["Heures"],
                format="%Y-%m-%d %H:%M",
                errors="coerce",
            )
            df = df.dropna(subset=["datetime"])
            df = df[df["datetime"].dt.minute.isin([0, 30])].copy()
            df = df.drop(columns=["Nature", "Date", "Heures"], errors="ignore")
            df = df.drop(axis=0, index=0)

            df["Périmètre"] = region
            df = df.reindex(columns=COLUMNS_ANALYSIS)
            for col in numeric_vars:
                df[col] = pd.to_numeric(
                    df[col]
                    .astype("string")
                    .str.strip()
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                )

            all_data.append(df)
            print(f"LOAD     | {file.name} : {len(df):,} lignes")

    if not all_data:
        raise FileNotFoundError(f"Aucun fichier .xls dans {raw_dir}")

    return (
        pd.concat(all_data, ignore_index=True)
        .sort_values(["Périmètre", "datetime"])
        .reset_index(drop=True)
    )


def save_data(df: pd.DataFrame, path: str | Path = OUTPUT_FILE) -> Path:
    """Sauvegarde les données dans un fichier Parquet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="snappy")
    print(f"SAVE     | {path}")
    return path


def load_saved_data(path: str | Path = OUTPUT_FILE) -> pd.DataFrame:
    """Charge le Parquet déjà créé, sans réexécuter le pipeline."""
    return pd.read_parquet(path)


def run_pipeline(force: bool = False) -> pd.DataFrame:
    """Télécharge → extrait → transforme → sauvegarde les données."""
    download_data_zip(force=force)
    extract_files(delete_zip=True)
    df = load_data_rte(RAW_DIR)
    save_data(df)
    print(f"DONE     | {df.shape[0]:,} lignes × {df.shape[1]} colonnes")
    return df


if __name__ == "__main__":
    run_pipeline()
