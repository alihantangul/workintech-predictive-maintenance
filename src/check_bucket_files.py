from io import BytesIO

import pandas as pd
from google.cloud import storage


PROJECT_ID = "predictive-maintenance-504421"
BUCKET_NAME = "pm-abb-data-93707"

FILES = [
    "raw/asset_93707/Asset_93707_MDEMAIG180-22B_2026-04.xlsx",
    "raw/asset_93707/Asset_93707_MDEMAIG180-22B_2026-04-2.xlsx",
]


client = storage.Client(project=PROJECT_ID)
bucket = client.bucket(BUCKET_NAME)

for file_name in FILES:
    blob = bucket.blob(file_name)
    file_bytes = blob.download_as_bytes()

    df = pd.read_excel(
        BytesIO(file_bytes),
        header=1,
        engine="calamine"
    )

    print("-" * 60)
    print(file_name)
    print("Shape:", df.shape)

    for index, column in enumerate(df.columns):
        print(index, column)