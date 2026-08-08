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
"""Burdan devam"""







