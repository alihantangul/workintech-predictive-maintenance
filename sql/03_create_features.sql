-- =========================================================
-- 03_create_features.sql
--
-- Amaç:
-- Clean tablodan modelin kullanabileceği özellikleri üretmek.
--
-- Bu aşamada:
-- 1. Yalnızca çalışan ve temel kalite kontrolünden geçen
--    kayıtlar alınır.
-- 2. Her çalışma modu için normal davranış seviyesi çıkarılır.
-- 3. Önceki değer, değişim, son 3 ölçüm ortalaması ve
--    normalden sapma kolonları oluşturulur.
-- =========================================================

CREATE OR REPLACE TABLE
`predictive-maintenance-504421.pm_features.motor_condition_features`

PARTITION BY DATE(Timestamp)
CLUSTER BY Asset_ID, Operating_Mode AS


-- ---------------------------------------------------------
-- 1. Modelde kullanılabilecek çalışan motor kayıtları
-- ---------------------------------------------------------
WITH running_data AS (

    SELECT
        *

    FROM
        `predictive-maintenance-504421.pm_clean.motor_measurements`

    WHERE
        Is_Running = TRUE

        AND Data_Quality_Flag IN (
            'OK',
            'MISSING_POWER'
        )

        AND Operating_Mode IN (
            'MODE_50HZ',
            'MODE_57HZ',
            'OTHER'
        )
),


-- ---------------------------------------------------------
-- 2. Her çalışma modu için temel normal davranış
-- ---------------------------------------------------------
mode_baseline AS (

    SELECT
        Asset_ID,
        Operating_Mode,

        COUNT(*) AS Baseline_Row_Count,

        -- Yönsel titreşim ortancaları
        APPROX_QUANTILES(
            Vib_Radial_mm_s,
            100
        )[OFFSET(50)] AS Median_Vib_Radial,

        APPROX_QUANTILES(
            Vib_Tangential_mm_s,
            100
        )[OFFSET(50)] AS Median_Vib_Tangential,

        APPROX_QUANTILES(
            Vib_Axial_mm_s,
            100
        )[OFFSET(50)] AS Median_Vib_Axial,

        -- Yüksek değer sınırları
        APPROX_QUANTILES(
            Vib_Radial_mm_s,
            100
        )[OFFSET(95)] AS P95_Vib_Radial,

        APPROX_QUANTILES(
            Vib_Tangential_mm_s,
            100
        )[OFFSET(95)] AS P95_Vib_Tangential,

        APPROX_QUANTILES(
            Vib_Axial_mm_s,
            100
        )[OFFSET(95)] AS P95_Vib_Axial,

        APPROX_QUANTILES(
            Acc_RMS_Tangential_g,
            100
        )[OFFSET(95)] AS P95_Acc_Tangential,

        APPROX_QUANTILES(
            Pk_Pk_Tangential_g,
            100
        )[OFFSET(95)] AS P95_Pk_Pk_Tangential,

        APPROX_QUANTILES(
            Skin_Temp_C,
            100
        )[OFFSET(50)] AS Median_Skin_Temp

    FROM running_data

    GROUP BY
        Asset_ID,
        Operating_Mode
),


-- ---------------------------------------------------------
-- 3. Önceki ölçüm ve hareketli değerler
-- ---------------------------------------------------------
window_features AS (

    SELECT
        r.*,

        -- Aynı motor ve çalışma modundaki önceki timestamp
        LAG(Timestamp) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Timestamp,

        -- Önceki titreşim değerleri
        LAG(Vib_Radial_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Vib_Radial,

        LAG(Vib_Tangential_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Vib_Tangential,

        LAG(Vib_Axial_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Vib_Axial,

        LAG(Acc_RMS_Tangential_g) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Acc_Tangential,

        LAG(Skin_Temp_C) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
        ) AS Previous_Skin_Temp,

        -- Son 3 aktif ölçümün titreşim ortalamaları
        AVG(Vib_Radial_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Avg_3_Vib_Radial,

        AVG(Vib_Tangential_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Avg_3_Vib_Tangential,

        AVG(Vib_Axial_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Avg_3_Vib_Axial,

        -- Son 3 aktif ölçümün maksimumları
        MAX(Vib_Tangential_mm_s) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Max_3_Vib_Tangential,

        MAX(Acc_RMS_Tangential_g) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Max_3_Acc_Tangential,

        MAX(Pk_Pk_Tangential_g) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Max_3_Pk_Pk_Tangential,

        AVG(Skin_Temp_C) OVER (
            PARTITION BY
                Asset_ID,
                Operating_Mode
            ORDER BY Timestamp
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS Avg_3_Skin_Temp

    FROM running_data AS r
),


-- ---------------------------------------------------------
-- 4. Baseline değerlerini ölçümlere ekleme
-- ---------------------------------------------------------
features_with_baseline AS (

    SELECT
        w.*,

        b.Baseline_Row_Count,

        b.Median_Vib_Radial,
        b.Median_Vib_Tangential,
        b.Median_Vib_Axial,

        b.P95_Vib_Radial,
        b.P95_Vib_Tangential,
        b.P95_Vib_Axial,
        b.P95_Acc_Tangential,
        b.P95_Pk_Pk_Tangential,

        b.Median_Skin_Temp

    FROM window_features AS w

    LEFT JOIN mode_baseline AS b
        USING (
            Asset_ID,
            Operating_Mode
        )
)


-- ---------------------------------------------------------
-- 5. Modelde kullanılacak nihai feature tablosu
-- ---------------------------------------------------------
SELECT
    Asset_ID,
    Timestamp,
    Operating_Mode,

    -- Mevcut çalışma değerleri
    Speed_rpm,
    Frequency_Hz,
    Output_Power_kW,
    Skin_Temp_C,

    Vib_Radial_mm_s,
    Vib_Tangential_mm_s,
    Vib_Axial_mm_s,

    Acc_RMS_Axial_g,
    Acc_RMS_Tangential_g,
    Acc_RMS_Radial_g,

    Pk_Pk_Tangential_g,

    -- Önceki aktif ölçüme kadar geçen süre
    TIMESTAMP_DIFF(
        Timestamp,
        Previous_Timestamp,
        HOUR
    ) AS Hours_Since_Previous_Measurement,

    -- Son ölçüme göre değişimler
    Vib_Radial_mm_s
        - Previous_Vib_Radial
        AS Change_Vib_Radial,

    Vib_Tangential_mm_s
        - Previous_Vib_Tangential
        AS Change_Vib_Tangential,

    Vib_Axial_mm_s
        - Previous_Vib_Axial
        AS Change_Vib_Axial,

    Acc_RMS_Tangential_g
        - Previous_Acc_Tangential
        AS Change_Acc_Tangential,

    Skin_Temp_C
        - Previous_Skin_Temp
        AS Change_Skin_Temp,

    -- Son üç aktif ölçüm
    Avg_3_Vib_Radial,
    Avg_3_Vib_Tangential,
    Avg_3_Vib_Axial,

    Max_3_Vib_Tangential,
    Max_3_Acc_Tangential,
    Max_3_Pk_Pk_Tangential,

    Avg_3_Skin_Temp,

    -- Çalışma modunun normal seviyesinden fark
    Vib_Radial_mm_s
        - Median_Vib_Radial
        AS Deviation_Vib_Radial,

    Vib_Tangential_mm_s
        - Median_Vib_Tangential
        AS Deviation_Vib_Tangential,

    Vib_Axial_mm_s
        - Median_Vib_Axial
        AS Deviation_Vib_Axial,

    Skin_Temp_C
        - Median_Skin_Temp
        AS Deviation_Skin_Temp,

    -- Normal değere oran
    SAFE_DIVIDE(
        Vib_Radial_mm_s,
        Median_Vib_Radial
    ) AS Ratio_Vib_Radial_To_Normal,

    SAFE_DIVIDE(
        Vib_Tangential_mm_s,
        Median_Vib_Tangential
    ) AS Ratio_Vib_Tangential_To_Normal,

    SAFE_DIVIDE(
        Vib_Axial_mm_s,
        Median_Vib_Axial
    ) AS Ratio_Vib_Axial_To_Normal,

    -- Mevcut değer çalışma modunun üst %5'inde mi?
    Vib_Radial_mm_s
        > P95_Vib_Radial
        AS Is_High_Vib_Radial,

    Vib_Tangential_mm_s
        > P95_Vib_Tangential
        AS Is_High_Vib_Tangential,

    Vib_Axial_mm_s
        > P95_Vib_Axial
        AS Is_High_Vib_Axial,

    Acc_RMS_Tangential_g
        > P95_Acc_Tangential
        AS Is_High_Acc_Tangential,

    Pk_Pk_Tangential_g
        > P95_Pk_Pk_Tangential
        AS Is_High_Pk_Pk_Tangential,

    -- Baseline'ın kaç kayıtla oluşturulduğu
    Baseline_Row_Count,

    Power_Missing,
    Load_Timestamp

FROM features_with_baseline;