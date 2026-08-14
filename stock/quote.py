from stock import ashare


def get_last_price(tscode, deci=2):
    """
    获取实时数据(采用1分钟K线等效）
    :param tscode: str sz000333
    :param deci: int 2或3，保留小数位数
    :return: 列表
    """
    try:
        df = ashare.get_price(code, frequency='1d', count=2)
        if df.empty:                    
            quote = ashare.get_price(code, frequency='1m', count=1) 
        df = df.sort_index()
        if len(df) >= 2:
            return df.iloc[-2]['close']
        elif len(df) == 1:
            # 只有今日数据（如新股），用今日开盘价替代
            return df.iloc[0]['open']
        return None
    except Exception:
        return None
