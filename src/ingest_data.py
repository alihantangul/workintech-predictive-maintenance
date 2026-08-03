from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
from google.cloud import bigquery, storage

from config import (
    ASSET_ID,
    BQ_STAGING_TABLE,
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    GCS_FILE_DIRECTIONAL,
    GCS_FILE_OPERATIONS,
)


def read_excel_from_gcs(object_name: str) -> pd.DataFrame:
    """Cloud Storage içindeki ABB Excel dosyasını okur."""

    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)

    if not blob.exists():
        raise FileNotFoundError(
            f"Bucket içinde dosya bulunamadı: {object_name}"
        )

    file_bytes = blob.download_as_bytes()

    return pd.read_excel(
        BytesIO(file_bytes),
        header=1,
        engine="calamine",
    )


def prepare_operations_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Operasyon ve genel durum dosyasındaki gerekli kolonları seçer."""

    df = pd.DataFrame()

    df["Timestamp"] = pd.to_datetime(
        df_raw.iloc[:, 0],
        errors="coerce",
    )

    df["Overall_Vib_mm_s"] = pd.to_numeric(
        df_raw.iloc[:, 2],
        errors="coerce",
    )

    df["Speed_rpm"] = pd.to_numeric(
        df_raw.iloc[:, 5],
        errors="coerce",
    )

    df["Skin_Temp_C"] = pd.to_numeric(
        df_raw.iloc[:, 8],
        errors="coerce",
    )

    df["Frequency_Hz"] = pd.to_numeric(
        df_raw.iloc[:, 11],
        errors="coerce",
    )

    df["Output_Power_kW"] = pd.to_numeric(
        df_raw.iloc[:, 14],
        errors="coerce",
    )

    df["Pk_Pk_Tangential_g"] = pd.to_numeric(
        df_raw.iloc[:, 17],
        errors="coerce",
    )

    return df


def prepare_directional_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Yönsel titreşim ve ivme dosyasındaki gerekli kolonları seçer."""

    df = pd.DataFrame()

    df["Timestamp"] = pd.to_datetime(
        df_raw.iloc[:, 0],
        errors="coerce",
    )

    df["Vib_Radial_mm_s"] = pd.to_numeric(
        df_raw.iloc[:, 2],
        errors="coerce",
    )

    df["Vib_Tangential_mm_s"] = pd.to_numeric(
        df_raw.iloc[:, 5],
        errors="coerce",
    )

    df["Vib_Axial_mm_s"] = pd.to_numeric(
        df_raw.iloc[:, 8],
        errors="coerce",
    )

    df["Acc_RMS_Axial_g"] = pd.to_numeric(
        df_raw.iloc[:, 11],
        errors="coerce",
    )

    df["Acc_RMS_Tangential_g"] = pd.to_numeric(
        df_raw.iloc[:, 14],
        errors="coerce",
    )

    df["Acc_RMS_Radial_g"] = pd.to_numeric(
        df_raw.iloc[:, 17],
        errors="coerce",
    )

    return df


def merge_data(
    operations: pd.DataFrame,
    directional: pd.DataFrame,
) -> pd.DataFrame:
    """İki ABB veri kaynağını Timestamp üzerinden birleştirir."""

    merged = pd.merge(
        operations,
        directional,
        on="Timestamp",
        how="outer",
        validate="one_to_one",
    )

    merged = (
        merged
        .dropna(subset=["Timestamp"])
        .sort_values("Timestamp")
        .drop_duplicates(subset=["Timestamp"], keep="last")
        .reset_index(drop=True)
    )

    merged["Asset_ID"] = ASSET_ID
    merged["Source_Operations_File"] = GCS_FILE_OPERATIONS
    merged["Source_Directional_File"] = GCS_FILE_DIRECTIONAL
    merged["Load_Timestamp"] = datetime.now(timezone.utc)

    return merged


def load_to_bigquery(dataframe: pd.DataFrame) -> None:
    """Hazırlanan DataFrame'i BigQuery staging tablosuna yükler."""

    bigquery_client = bigquery.Client(project=GCP_PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    load_job = bigquery_client.load_table_from_dataframe(
        dataframe,
        BQ_STAGING_TABLE,
        job_config=job_config,
    )

    load_job.result()

    print(
        f"{len(dataframe)} satır BigQuery'ye yüklendi:\n"
        f"{BQ_STAGING_TABLE}"
    )


def main() -> None:
    print("Bucket içindeki ABB dosyaları okunuyor...")

    operations_raw = read_excel_from_gcs(
        GCS_FILE_OPERATIONS
    )

    directional_raw = read_excel_from_gcs(
        GCS_FILE_DIRECTIONAL
    )

    operations = prepare_operations_data(
        operations_raw
    )

    directional = prepare_directional_data(
        directional_raw
    )

    merged = merge_data(
        operations,
        directional,
    )

    print("-" * 50)
    print("VERİ HAZIRLAMA TAMAMLANDI")
    print(f"Toplam satır: {len(merged)}")
    print(f"Kolon sayısı: {len(merged.columns)}")
    print(f"Motor açık kayıt: {(merged['Speed_rpm'] > 0).sum()}")
    print(f"Motor kapalı kayıt: {(merged['Speed_rpm'] == 0).sum()}")
    print("-" * 50)

    print(merged.head())

    load_to_bigquery(merged)


if __name__ == "__main__":
    main()