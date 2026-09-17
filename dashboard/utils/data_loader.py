from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "test_df.csv"


def load_data():
    """대시보드용 조달 데이터를 불러온다."""

    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["contract_date", "delivery_date"]
    )

    return df