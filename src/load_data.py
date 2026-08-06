"""
load_data.py

Asset 93707 (MDEMAIG180-22B) - Sensor exportlarini yukler.

Her .xlsx dosyasinda ayni yapida tekrarlayan metrik bloklari var:
    [Metrik Adi]
    Timestamp UTC | Timestamp local | Value (birim)
    ...

Bu script:
    1. Her metrik blogunu okuyup "Value" kolonunu "<Metrik Adi> Value" olarak
       yeniden adlandirir (orn. "Vibration (Radial) Value").
    2. Timestamp UTC + Timestamp Local'i index yapar (tum bloklarda ayni oldugu icin).
    3. Ayni dosyadaki tum metrik bloklarini bu timestamp index uzerinden
       yan yana birlestirir (tek satirda tum metrikler).
    4. data/raw/ klasorundeki tum .xlsx dosyalarini (orn. Asset_93707_MDEMAIG180-22B_2026-04.xlsx
       ve ...2026-04-2.xlsx) ayni timestamp index'i uzerinden YAN YANA (outer join)
       birlestirir -> tek satirda tum dosyalardaki tum metrikler bir arada olur.
       Iki dosyada da ayni isimde bir metrik kolonu varsa, hangi dosyadan geldigi
       belli olsun diye kolon adina dosya adi eklenir (orn. "Vibration (Radial)
       Value (Asset_93707_MDEMAIG180-22B_2026-04-2)").

Proje yapisi (src/load_data.py buradan calisir, yollar otomatik bulunur):
    workintech-predictive-maintenance/
      data/
        raw/           <- .xlsx export dosyalari buraya
        processed/     <- cikti parquet buraya yazilir
      src/
        load_data.py

Kullanim (src/ klasorunden):
    python load_data.py

Gereksinimler:
    pip install python-calamine pandas pyarrow --break-system-packages
"""

import glob
import os

import pandas as pd

# --- Proje yapisi (workintech-predictive-maintenance) ---
# Bu dosya src/load_data.py altinda oldugu icin, VSCode'da nereden calistirilirsa
# calistirilsin dogru klasorleri bulabilmesi icin yollari __file__'a gore kuruyoruz.

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/'nin bir ustu
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUT_FILE = os.path.join(PROCESSED_DATA_DIR, "asset_93707_merged.csv")


def load_sensor_file(filepath: str) -> pd.DataFrame:
    """
    Tek bir ABB export dosyasini okuyup wide (genis) formata cevirir.

    Donen DataFrame:
        index   = (Timestamp UTC, Timestamp Local)
        columns = "<Metrik Adi> Value" (dosyadaki her metrik blogu icin bir kolon)

    Not: Ayni satirdaki tum metrik bloklari ayni saatin okumasidir. Bazen bir
    blokta sadece o metrigin degeri olcumsuz kaldigi icin o blogun kendi
    Timestamp UTC/Local hucreleri de bos gelir (orn. Output Power). Bu durumda
    o satirin gercek zamani, ayni satirdaki DIGER bloklarin timestamp'inden
    alinir (zaman hepsinde ayni oldugu icin) -- deger (Value) yine de gercekten
    olculmedigi icin NaN olarak kalir, sadece zaman bilgisi kaybolmaz.
    """
    raw = pd.read_excel(filepath, sheet_name=0, header=None, engine="calamine")

    # 1. satirda grup adi sadece bloğun ilk kolonunda var, digerleri NaN -> ffill ile doldur
    group_row = raw.iloc[0].ffill()
    data = raw.iloc[2:].reset_index(drop=True)  # veri 3. satirdan basliyor

    n_cols = raw.shape[1]
    utc_cols = list(range(0, n_cols, 3))
    local_cols = list(range(1, n_cols, 3))

    # Her blogun kendi Timestamp UTC / Local kolonlarini ayri ayri parse et
    utc_matrix = data.iloc[:, utc_cols].apply(pd.to_datetime)
    local_matrix = data.iloc[:, local_cols].apply(pd.to_datetime)

    # Satir bazinda "kanonik" timestamp: o satirda hangi blokta timestamp
    # doluysa onu kullan (hepsi ayni zamani temsil ettigi icin fark etmez).
    # bfill(axis=1) her satirda soldan saga ilk dolu degeri bulup NaN'lari
    # onunla doldurur; iloc[:, 0] o satirdaki ilk gecerli degeri verir.
    canonical_utc = utc_matrix.bfill(axis=1).iloc[:, 0]
    canonical_local = local_matrix.bfill(axis=1).iloc[:, 0]

    # Hicbir blokta timestamp yoksa (satir tamamen bos) kanonik deger de NaT
    # kalir -- bu satirin zaman referansi hic yok demektir, bu satirlari ayri
    # tutup bilgi olarak raporluyoruz.
    fully_blank_rows = canonical_utc.isna()
    if fully_blank_rows.any():
        print(
            f"  [uyari] '{os.path.basename(filepath)}': {fully_blank_rows.sum()} "
            f"satirda HICBIR blokta timestamp yok (tamamen bos satir), bu "
            f"satirlar atlandi."
        )

    blocks = []
    for i, start in enumerate(range(0, n_cols, 3)):
        utc_col, local_col, value_col = start, start + 1, start + 2
        metric_name = str(group_row[utc_col]).strip()
        value_col_name = f"{metric_name} Value"

        # Bu blogun kendi timestamp'i eksik olup kanonik timestamp'ten
        # dolduruldugu satir sayisini raporla

        own_missing = utc_matrix.iloc[:, i].isna() & ~fully_blank_rows
        if own_missing.any():
            print(
                f"  [bilgi] '{os.path.basename(filepath)}' / '{metric_name}': "
                f"{own_missing.sum()} satirda bu metrigin kendi timestamp'i "
                f"bos, ayni satirdaki diger bloklardan dolduruldu (deger "
                f"yine de olculmedigi icin NaN kalacak)."
            )

        value = pd.to_numeric(data.iloc[:, value_col], errors="coerce")

        block = pd.DataFrame({
            "Timestamp UTC": canonical_utc,
            "Timestamp Local": canonical_local,
            value_col_name: value,
        })
        block = block[~fully_blank_rows]  # zaman referansi olmayan satirlari at
        block = block.set_index(["Timestamp UTC", "Timestamp Local"])

        # Gercek duplicate kontrolu: ayni timestamp ayni blokta birden fazla
        # kez gorunuyorsa bu bir veri kalitesi sorunu olabilir, sessizce
        # silmiyoruz -- nerede oldugunu gosterip duruyoruz.

        dup_mask = block.index.duplicated(keep=False)
        if dup_mask.any():
            dup_examples = block[dup_mask].sort_index()
            raise ValueError(
                f"'{os.path.basename(filepath)}' dosyasinda '{metric_name}' blogunda "
                f"{dup_mask.sum()} satirda duplicate timestamp bulundu (toplam "
                f"{block.index.duplicated().sum()} tekrar). Bu satirlarin orijinal "
                f"Excel dosyasinda neden tekrarlandigini kontrol et:\n"
                f"{dup_examples.head(10)}"
            )

        blocks.append(block)

    wide = pd.concat(blocks, axis=1)
    wide["source_file"] = os.path.basename(filepath)
    return wide


def load_and_merge_all(raw_dir: str = RAW_DATA_DIR) -> pd.DataFrame:

    """
    raw_dir icindeki tum .xlsx dosyalarini load_sensor_file ile isler ve
    (Timestamp UTC, Timestamp Local) index'i uzerinden YAN YANA (outer join)
    birlestirir. Sonuc: her timestamp icin tum dosyalardaki tum metrik
    kolonlari tek satirda bir arada olur.

    Iki dosyada ayni isimde bir kolon varsa (orn. ayni metrik iki dosyada da
    varsa), cakismayi onlemek icin kolon adina dosya adi eklenir.
    """

    filepaths = sorted(glob.glob(os.path.join(raw_dir, "*.xlsx")))
    if not filepaths:
        raise FileNotFoundError(f"'{raw_dir}' icinde .xlsx dosyasi bulunamadi.")

    merged = None
    for fp in filepaths:
        df = load_sensor_file(fp).drop(columns=["source_file"])
        file_tag = os.path.splitext(os.path.basename(fp))[0]

        if merged is None:
            merged = df
            continue

        overlap = merged.columns.intersection(df.columns)
        if len(overlap) > 0:
            df = df.rename(columns={c: f"{c} ({file_tag})" for c in overlap})

        # load_sensor_file her dosyanin kendi icinde timestamp'lerin tekil
        # oldugunu zaten garanti ediyor (aksi halde orada hata firlar), o
        # yuzden burada sessiz bir dedup yapmiyoruz.

        merged = merged.join(df, how="outer")

    merged = merged.sort_index(level="Timestamp UTC")
    return merged


if __name__ == "__main__":
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    df = load_and_merge_all()

    print(f"Sekil: {df.shape}")
    print(f"Tarih araligi: {df.index.get_level_values('Timestamp UTC').min()} -> "
          f"{df.index.get_level_values('Timestamp UTC').max()}")
    print(df.head())

    df.to_csv(OUTPUT_FILE)
    print(f"Birlestirilmis veri kaydedildi: {OUTPUT_FILE}")
    print(
        "[not] Parquet yerine CSV'ye kaydedildi cunku pyarrow/fastparquet "
        "ortaminda kurulu degil. pyarrow kurulumu sorunu cozulunce "
        "OUTPUT_FILE'i tekrar '.parquet' yapip df.to_parquet(OUTPUT_FILE) "
        "kullanabilirsin (multiindex ve dtype'lar otomatik korunur, CSV'de "
        "ise geri okurken index_col=[0,1] ve parse_dates ile tekrar "
        "kurman gerekir)."
    )