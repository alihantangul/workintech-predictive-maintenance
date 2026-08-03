-- =========================================================
-- 04_create_training_dataset.sql
--
-- Amaç:
-- Mevcut sensör özelliklerinden anormal durum etiketi ve
-- sonraki 3 aktif ölçümde anormal durum oluşup oluşmayacağını
-- gösteren Future_Event hedefini üretmek.
-- =========================================================

CREATE OR REPLACE TABLE
`predictive-maintenance-504421.pm_features.training_dataset`

PARTITION BY DATE(Timestamp)
CLUSTER BY Asset_ID, Operating_Mode AS


-- ---------------------------------------------------------
-- 1. Mevcut ölçüm anormal mi?
-- ---------------------------------------------------------
WITH current_events AS (

    SELECT
        *,

        -- Birden fazla göstergenin aynı anda yükselmesi,
        -- tek bir sensör sıçramasından daha anlamlıdır.
        CAST(Is_High_Vib_Radial AS INT64)
        + CAST(Is_High_Vib_Tangential AS INT64)
        + CAST(Is_High_Vib_Axial AS INT64)
        + CAST(Is_High_Acc_Tangential AS INT64)
        + CAST(Is_High_Pk_Pk_Tangential AS INT64)
            AS Anomaly_Indicator_Count,

        CASE
            -- En az iki gösterge aynı anda yüksekse anormal
            WHEN (
                CAST(Is_High_Vib_Radial AS INT64)
                + CAST(Is_High_Vib_Tangential AS INT64)
                + CAST(Is_High_Vib_Axial AS INT64)
                + CAST(Is_High_Acc_Tangential AS INT64)
                + CAST(Is_High_Pk_Pk_Tangential AS INT64)
            ) >= 2
                THEN 1

            ELSE 0
        END AS Current_Anomaly

    FROM
        `predictive-maintenance-504421.pm_features.motor_condition_features`
),


-- ---------------------------------------------------------
-- 2. Sonraki aktif ölçümlerdeki anormal durumları getir
-- ---------------------------------------------------------
future_events AS (

    SELECT
        *,

        LEAD(Current_Anomaly, 1) OVER (
            PARTITION BY Asset_ID
            ORDER BY Timestamp
        ) AS Anomaly_Next_1,

        LEAD(Current_Anomaly, 2) OVER (
            PARTITION BY Asset_ID
            ORDER BY Timestamp
        ) AS Anomaly_Next_2,

        LEAD(Current_Anomaly, 3) OVER (
            PARTITION BY Asset_ID
            ORDER BY Timestamp
        ) AS Anomaly_Next_3

    FROM current_events
),


-- ---------------------------------------------------------
-- 3. Zaman sırasına göre eğitim/test sırası oluştur
-- ---------------------------------------------------------
ordered_data AS (

    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY Asset_ID
            ORDER BY Timestamp
        ) AS Time_Row_Number,

        COUNT(*) OVER (
            PARTITION BY Asset_ID
        ) AS Total_Asset_Rows

    FROM future_events
)


-- ---------------------------------------------------------
-- 4. Nihai eğitim tablosu
-- ---------------------------------------------------------
SELECT
    * EXCEPT(
        Anomaly_Next_1,
        Anomaly_Next_2,
        Anomaly_Next_3,
        Time_Row_Number,
        Total_Asset_Rows
    ),

    -- Sonraki üç aktif ölçümden herhangi biri anormalse 1
    CASE
        WHEN Anomaly_Next_1 = 1
            OR Anomaly_Next_2 = 1
            OR Anomaly_Next_3 = 1
            THEN 1

        ELSE 0
    END AS Future_Event,

    -- Veriyi rastgele değil, zaman sırasına göre bölüyoruz.
    CASE
        WHEN SAFE_DIVIDE(
            Time_Row_Number,
            Total_Asset_Rows
        ) <= 0.70
            THEN 'TRAIN'

        WHEN SAFE_DIVIDE(
            Time_Row_Number,
            Total_Asset_Rows
        ) <= 0.85
            THEN 'VALIDATION'

        ELSE 'TEST'
    END AS Data_Split

FROM ordered_data

-- Son üç satır için geleceği bilemeyeceğimizden çıkarıyoruz.
WHERE
    Anomaly_Next_1 IS NOT NULL
    AND Anomaly_Next_2 IS NOT NULL
    AND Anomaly_Next_3 IS NOT NULL;