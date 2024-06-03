from math import radians, sin, cos, sqrt, atan2


def get_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    利用Haversine公式計算兩點之間的距離

    :param lat1: 第一點的緯度
    :param lon1: 第一點的經度
    :param lat2: 第二點的緯度
    :param lon2: 第二點的經度
    :return: 兩點之間的距離，單位公里
    """

    R = 6371.0  # 地球半徑，單位公里

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return round(distance, 2)
