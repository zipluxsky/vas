import datetime


def get_rpt_date(flag: bool, offset: int, ref_date: datetime.date) -> str:
    """Return the previous business day as YYYYMMDD string.

    Skips Saturdays, Sundays and January 1st of every year.
    """
    d = ref_date
    while True:
        d -= datetime.timedelta(days=1)
        if d.weekday() >= 5:
            continue
        if d.month == 1 and d.day == 1:
            continue
        break
    return d.strftime("%Y%m%d")


def build_region_filter(hour: int, trade_date_arg: str) -> tuple:
    """Determine market region filter based on current hour.

    Returns (strRegion, mkt) where strRegion is the SQL fragment and mkt is
    a label ('All' or 'US').
    """
    mkt = "All"
    str_region = " or 1=1 "
    if hour < 10 and trade_date_arg == "19000101":
        str_region = ""
        mkt = "US"
    return str_region, mkt
