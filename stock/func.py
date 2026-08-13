import pandas as pd
import datetime


def date_to_timestamp(date_obj):
    """日期转13位毫秒时间戳"""
    if isinstance(date_obj, str):
        date_obj = pd.to_datetime(date_obj)
    
    return int(date_obj.timestamp() * 1000)
