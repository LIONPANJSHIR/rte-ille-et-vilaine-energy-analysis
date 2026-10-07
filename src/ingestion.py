from pathlib import Path
from zipfile import ZipFile

import requests


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(r"C:\Full_stack\Portfolios\Projets\Data_Analysis_Projects\rte")

RAW_DIR = PROJECT_DIR / "data" / "raw"

REGION_SLUGS = {
    "Auvergne-Rhône-Alpes": "Auvergne-Rh%C3%B4ne-Alpes",
    "Bretagne": "Bretagne",
}

YEARS = range(2013, 2025)


# ============================================================
# DOWNLOAD
# ============================================================


def download_data_zip() -> None:
    for region, region_url in REGION_SLUGS.items():
        output_dir = RAW_DIR / region
        output_dir.mkdir(parents=True, exist_ok=True)

        for year in YEARS:
            filename = f"eCO2mix_RTE_{region}_Annuel-Definitif_{year}.zip"

            output_file = output_dir / filename

            # Ne pas retélécharger
            if output_file.exists():
                print(f"⏭️ Déjà présent : {region} - {year}")
                continue

            url = (
                "https://eco2mix.rte-france.com/"
                "download/eco2mix/"
                f"eCO2mix_RTE_{region_url}_"
                f"Annuel-Definitif_{year}.zip"
            )

            print(f"⬇️ Téléchargement : {region} - {year}")

            response = requests.get(url, timeout=60)

            response.raise_for_status()

            output_file.write_bytes(response.content)

            print(f"✅ {region} - {year}")


# ============================================================
# EXTRACTION
# ============================================================


def extract_files(delete_zip: bool = True, delete_empty_dirs: bool = True) -> None:
    extract_root = RAW_DIR

    for region in REGION_SLUGS:
        zip_dir = RAW_DIR / region
        extract_dir = extract_root / region

        extract_dir.mkdir(parents=True, exist_ok=True)

        if not zip_dir.exists():
            continue

        for zip_path in sorted(zip_dir.glob("*.zip")):
            try:
                with ZipFile(zip_path, "r") as zip_file:
                    zip_file.extractall(extract_dir)

                print(f"✅ Extraction réussie : {zip_path.name}")

                if delete_zip:
                    zip_path.unlink()
                    print(f"🗑️ ZIP supprimé : {zip_path.name}")

            except Exception as error:
                print(f"❌ Erreur : {zip_path.name}")
                print(error)

        # supprimer le dossier source seulement s'il est vide
        if delete_empty_dirs:
            try:
                zip_dir.rmdir()
                print(f"🗑️ Dossier supprimé : {zip_dir.name}")

            except OSError:
                print(f"⚠️ Dossier non vide, conservé : {zip_dir}")


if __name__ == "__main__":
    download_data_zip()
    extract_files()
