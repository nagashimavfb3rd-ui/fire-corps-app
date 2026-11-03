
from datetime import date, datetime


def calc_age(birth_date):
    """生年月日から現在の年齢を計算する"""
    if not birth_date:
        return None

    birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()

    return today.year - birth.year - (
        (today.month, today.day) < (birth.month, birth.day)
    )
