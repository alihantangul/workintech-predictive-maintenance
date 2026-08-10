# Feature Engineering for Predictive Maintenance

import glob
import os
import numpy as np
import pandas as pd
import xy
import plotly.express as px

# --- Proje yapisi (workintech-predictive-maintenance) ---
# Bu dosya src/load_data.py altinda oldugu icin, VSCode'da nereden calistirilirsa
# calistirilsin dogru klasorleri bulabilmesi icin yollari __file__'a gore kuruyoruz.

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
MERGED_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "asset_93707_merged.csv")
FEATURES_FILE = os.path.join(PROJECT_ROOT, "data","processed","asset_93707_features.csv")


#processed data fileini oku, csv'yi dataframe'e cevir.

def load_merged(filepath: str=MERGED_FILE) -> pd.DataFrame:

    df = pd.read_csv(filepath, index_col='timestamp_utc')
    df.index.name = 'timestamp_utc'
    return df

df=load_merged()

# 1. Eksenel Titreşim / Güç Oranı (Kaplin Sağlığı Göstergesi)
# Çıkış gücü 0'a çok yakınsa sonsuza gitmemesi için ufak bir epsilon (0.01) ekliyoruz
df['axial_per_kW'] = df['vibration_axial_value'] / (df['output_power_value'] + 0.01)

#---#Burayı deneyeceğiz---
"""
chart = xy.line_chart(
    xy.line(df.index, df["axial_per_kW"], name="Axial Vibration per kW"),
)
chart.to_html('charts/axial_per_kW.html')
"""


# 2. Radyal İvme / Hız Oranı (Rulman Sağlığı Göstergesi - 1000 devir başına normalize)
df['radial_acc_per_RPM'] = df['acceleration_rms_radial_value'] / (df['speed_value'] / 1000)


# 3. Toplam Titreşim Enerjisi (3 Eksenin Vektörel Bileşkesi)
df['Total_Vib_Energy'] = np.sqrt(
    df['vibration_axial_value']**2 +
    df['vibration_radial_value']**2 +
    df['vibration_tangential_value']**2
)


#4. Sıcaklık Mekanik Sürtünme Çarpanı
df['temp_vibration_factor'] = df['skin_temperature_value'] * df['overall_vibration_value']


thresholds = {'overall_vibration_value':{'alert': 9.13, 'alarm': 16.74},
                'peak_to_peak_tangential_value':{'alert': 1.53, 'alarm': 2.29},
                'skin_temperature_value':{'alert': 43.12, 'alarm': 60.0}}


"""
def generate_alerts(df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:

    #Verilen eşik değerlerine göre uyarı ve alarm sütunlarını oluşturur.
    for feature, limits in thresholds.items():
        alert_col = f"{feature}_alert"
        alarm_col = f"{feature}_alarm"
        
        df[alert_col] = df[feature].apply(lambda x: 100 if x<limits['alert']
                                           else ( 0 if x>limits['alarm'] else (1-(x-limits['alert']) / (limits['alarm'] - limits['alert']))* 100))
    
    return df
"""

# 2. Her bir özellik için 0-100 arası alt-skor hesaplayan dinamik ceza fonksiyonu
def calculate_sub_score(val, alert, alarm):
    # Eğer değer Alert'ten küçükse %100 sağlıklı
    # Eğer Alert ile Alarm arasındaysa skor 100'den 80'e doğru düşer
    # Eğer Alarm'ı geçerse skor 80'den 0'a çok daha sert bir ivmeyle düşer
    score = np.where(
        val <= alert, 100,
        np.where(
            val < alarm,
            100 - 20 * ((val - alert) / (alarm - alert)),
            80 - 80 * ((val - alarm) / (alarm * 0.5)) # Alarmın %50 fazlasına ulaşınca sistem %0 (Tam Arıza) olur
        )
    )
    return np.clip(score, 0, 100) # Skoru 0 ile 100 arasına sıkıştırıyoruz


df['peak_to_peak_sub_score'] =calculate_sub_score(df['peak_to_peak_tangential_value'], thresholds['peak_to_peak_tangential_value']['alert'], thresholds['peak_to_peak_tangential_value']['alarm'])
df['overall_vibration_sub_score'] = calculate_sub_score(df['overall_vibration_value'], thresholds['overall_vibration_value']['alert'], thresholds['overall_vibration_value']['alarm'])
df['skin_temperature_sub_score'] = calculate_sub_score(df['skin_temperature_value'], thresholds['skin_temperature_value']['alert'], thresholds['skin_temperature_value']['alarm'])


os.makedirs(os.path.dirname(FEATURES_FILE), exist_ok=True)
df.to_csv(FEATURES_FILE)
print(f"Feature'lar kaydedildi: {FEATURES_FILE}")



