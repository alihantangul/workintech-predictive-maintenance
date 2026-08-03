-- =========================================================
-- 02_create_clean.sql
--
-- Amaç:
-- Kalıcı RAW tablodaki verileri analiz için anlamlandırmak.
-- Satırları silmek yerine çalışma durumu, eksiklik ve
-- veri kalitesi kolonları oluşturmak.
-- =========================================================

CREATE OR REPLACE TABLE
`predictive-maintenance-504421.pm_clean.motor_measurements`

PARTITION BY DATE(Timestamp)
CLUSTER BY Asset_ID, Operating_Mode AS

WITH prepared AS (
    SELECT
        *,

        -- Üç yönsel titreşimden en yüksek olanı hesapla.
        -- NULL değerleri mümkün olduğunca göz ardı eder.
        (
            SELECT MAX(value)
            FROM UNNEST([
                Vib_Radial_mm_s,
                Vib_Tangential_mm_s,
                Vib_Axial_mm_s
            ]) AS value
            WHERE value IS NOT NULL
        ) AS Calculated_Overall_Vib_mm_s

    FROM
        `predictive-maintenance-504421.pm_raw.motor_measurements`
)

SELECT
    Asset_ID,
    Timestamp,

    Speed_rpm,
    Frequency_Hz,
    Output_Power_kW,
    Skin_Temp_C,

    Overall_Vib_mm_s,
    Vib_Radial_mm_s,
    Vib_Tangential_mm_s,
    Vib_Axial_mm_s,

    Acc_RMS_Axial_g,
    Acc_RMS_Tangential_g,
    Acc_RMS_Radial_g,
    Pk_Pk_Tangential_g,

    Calculated_Overall_Vib_mm_s,

    -- Motorun çalışma durumu
    CASE
        WHEN Speed_rpm > 0 THEN TRUE
        ELSE FALSE
    END AS Is_Running,

    -- Basit çalışma modu sınıflandırması
    CASE
        WHEN Speed_rpm IS NULL
            OR Frequency_Hz IS NULL
            THEN 'UNKNOWN'

        WHEN Speed_rpm = 0
            AND Frequency_Hz = 0
            THEN 'OFF'

        WHEN Frequency_Hz BETWEEN 49 AND 51
            THEN 'MODE_50HZ'

        WHEN Frequency_Hz BETWEEN 56 AND 58
            THEN 'MODE_57HZ'

        ELSE 'OTHER'
    END AS Operating_Mode,

    -- Eksik veri göstergeleri
    Output_Power_kW IS NULL AS Power_Missing,
    Skin_Temp_C IS NULL AS Temperature_Missing,

    (
        Vib_Radial_mm_s IS NULL
        OR Vib_Tangential_mm_s IS NULL
        OR Vib_Axial_mm_s IS NULL
    ) AS Directional_Vibration_Missing,

    (
        Acc_RMS_Axial_g IS NULL
        OR Acc_RMS_Tangential_g IS NULL
        OR Acc_RMS_Radial_g IS NULL
    ) AS Acceleration_Missing,

    -- ABB overall değerinin yönsel maksimumla uyumu
    CASE
        WHEN Overall_Vib_mm_s IS NULL
            OR Calculated_Overall_Vib_mm_s IS NULL
            THEN NULL

        WHEN ABS(
            Overall_Vib_mm_s
            - Calculated_Overall_Vib_mm_s
        ) <= 0.001
            THEN TRUE

        ELSE FALSE
    END AS Overall_Matches_Directional,

    -- Tek bir özet kalite etiketi
    CASE
        WHEN Speed_rpm < 0
            THEN 'INVALID_SPEED'

        WHEN Frequency_Hz < 0
            OR Frequency_Hz > 100
            THEN 'INVALID_FREQUENCY'

        WHEN Skin_Temp_C < -20
            OR Skin_Temp_C > 150
            THEN 'INVALID_TEMPERATURE'

        WHEN Output_Power_kW < 0
            THEN 'INVALID_POWER'

        WHEN Overall_Vib_mm_s < 0
            OR Vib_Radial_mm_s < 0
            OR Vib_Tangential_mm_s < 0
            OR Vib_Axial_mm_s < 0
            THEN 'INVALID_VIBRATION'

        WHEN Speed_rpm = 0
            AND Overall_Vib_mm_s > 2
            THEN 'OFF_STATE_HIGH_VIBRATION'

        WHEN Output_Power_kW IS NULL
            THEN 'MISSING_POWER'

        WHEN Vib_Radial_mm_s IS NULL
            OR Vib_Tangential_mm_s IS NULL
            OR Vib_Axial_mm_s IS NULL
            THEN 'MISSING_DIRECTIONAL_VIBRATION'

        ELSE 'OK'
    END AS Data_Quality_Flag,

    Source_Operations_File,
    Source_Directional_File,
    Load_Timestamp

FROM prepared
WHERE Timestamp IS NOT NULL;