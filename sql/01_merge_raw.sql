-- =========================================================
-- 01_merge_raw.sql
--
-- Amaç:
-- Staging tablodaki kayıtları kalıcı RAW tabloya taşımak.
-- Aynı Asset_ID + Timestamp daha önce varsa güncellemek,
-- yoksa yeni satır olarak eklemek.
-- =========================================================


-- 1. Kalıcı RAW tablo yoksa staging şemasıyla oluştur
CREATE TABLE IF NOT EXISTS
`predictive-maintenance-504421.pm_raw.motor_measurements`
LIKE
`predictive-maintenance-504421.pm_raw.motor_measurements_staging`;


-- 2. Staging tablodaki en güncel kayıtları RAW tabloya aktar
MERGE
`predictive-maintenance-504421.pm_raw.motor_measurements` AS target

USING (
    SELECT
        * EXCEPT(row_number)

    FROM (
        SELECT
            *,

            ROW_NUMBER() OVER (
                PARTITION BY
                    Asset_ID,
                    Timestamp

                ORDER BY
                    Load_Timestamp DESC
            ) AS row_number

        FROM
            `predictive-maintenance-504421.pm_raw.motor_measurements_staging`
    )

    WHERE row_number = 1
) AS source

ON
    target.Asset_ID = source.Asset_ID
    AND target.Timestamp = source.Timestamp


-- Aynı kayıt bulunursa en son yüklenen değerlerle güncelle
WHEN MATCHED THEN
    UPDATE SET

        Overall_Vib_mm_s =
            source.Overall_Vib_mm_s,

        Speed_rpm =
            source.Speed_rpm,

        Skin_Temp_C =
            source.Skin_Temp_C,

        Frequency_Hz =
            source.Frequency_Hz,

        Output_Power_kW =
            source.Output_Power_kW,

        Pk_Pk_Tangential_g =
            source.Pk_Pk_Tangential_g,

        Vib_Radial_mm_s =
            source.Vib_Radial_mm_s,

        Vib_Tangential_mm_s =
            source.Vib_Tangential_mm_s,

        Vib_Axial_mm_s =
            source.Vib_Axial_mm_s,

        Acc_RMS_Axial_g =
            source.Acc_RMS_Axial_g,

        Acc_RMS_Tangential_g =
            source.Acc_RMS_Tangential_g,

        Acc_RMS_Radial_g =
            source.Acc_RMS_Radial_g,

        Source_Operations_File =
            source.Source_Operations_File,

        Source_Directional_File =
            source.Source_Directional_File,

        Load_Timestamp =
            source.Load_Timestamp


-- Kayıt daha önce yoksa yeni satır olarak ekle
WHEN NOT MATCHED THEN
    INSERT ROW;