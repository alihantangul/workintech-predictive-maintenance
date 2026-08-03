from pathlib import Path
import os

from dotenv import load_dotenv


# Projenin ana klasörü
BASE_DIR = Path(__file__).resolve().parent.parent

# .env dosyasındaki değişkenleri yükler
load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# Yerel dosya yolları
# --------------------------------------------------

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

FILE_OPERATIONS = RAW_DATA_DIR / (
    "Asset_93707_MDEMAIG180-22B_2026-04.xlsx"
)

FILE_DIRECTIONAL = RAW_DATA_DIR / (
    "Asset_93707_MDEMAIG180-22B_2026-04-2.xlsx"
)


# --------------------------------------------------
# Google Cloud ayarları
# --------------------------------------------------

GCP_PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "predictive-maintenance-504421",
)

GCS_BUCKET_NAME = os.getenv(
    "GCS_BUCKET_NAME",
    "pm-abb-data-93707",
)


# --------------------------------------------------
# Cloud Storage içindeki dosya yolları
# --------------------------------------------------

GCS_FILE_OPERATIONS = (
    "raw/asset_93707/"
    "Asset_93707_MDEMAIG180-22B_2026-04-2.xlsx"
)

GCS_FILE_DIRECTIONAL = (
    "raw/asset_93707/"
    "Asset_93707_MDEMAIG180-22B_2026-04.xlsx"
)


# --------------------------------------------------
# BigQuery ayarları
# --------------------------------------------------

BQ_STAGING_TABLE = os.getenv(
    "BQ_STAGING_TABLE",
    (
        f"{GCP_PROJECT_ID}."
        "pm_raw.motor_measurements_staging"
    ),
)

BQ_RAW_TABLE = os.getenv(
    "BQ_RAW_TABLE",
    (
        f"{GCP_PROJECT_ID}."
        "pm_raw.motor_measurements"
    ),
)

BQ_CLEAN_TABLE = os.getenv(
    "BQ_CLEAN_TABLE",
    (
        f"{GCP_PROJECT_ID}."
        "pm_clean.motor_measurements"
    ),
)

BQ_FEATURE_TABLE = os.getenv(
    "BQ_FEATURE_TABLE",
    (
        f"{GCP_PROJECT_ID}."
        "pm_features.motor_condition_features"
    ),
)


# --------------------------------------------------
# Asset bilgileri
# --------------------------------------------------

ASSET_ID = 93707
ASSET_NAME = "MDEMAIG180-22B"
DATA_PERIOD = "2026-04"