"""Today's date, in one place so tests can fix it."""

import datetime as dt


def today() -> dt.date:
    return dt.date.today()
