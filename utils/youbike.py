from pprint import pprint
import requests
import pandas as pd
from utils.distance import get_distance


class YouBike:
    def __init__(self):
        self.url = "https://apis.youbike.com.tw/json/station-yb2.json"
        self.stations = self._get_stations()

    def _get_stations(self) -> pd.DataFrame:
        """
        Get YouBike stations data from the API
        :return: DataFrame
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'Cookie': 'incap_ses_934_3077348=y3lIbYgRWxRLJOQqGzz2DGjmV2YAAAAASDCG+d18tqIk06C+PWvl/g==; visid_incap_3077348=mGHCcVZDQQOaijO2DTFt+OpET2YAAAAAQUIPAAAAAAD+Mk9vP0UnWWUbA5D9v922',
        }
        response = requests.get(self.url, headers=headers)
        data = response.json()

        return pd.DataFrame(data)

    def get_stations_from_district(self, district):
        """
        Filter the stations by district
        :param district: str
        :return: DataFrame
        """
        return self.stations[self.stations["district_tw"] == district]

    def get_stations_spaces(self, station_no: str) -> tuple:
        """
        Get the available and empty spaces of a station
        :param station_no: str
        :return: tuple
        """
        available_spaces = self.stations[self.stations["station_no"] == station_no][
            'available_spaces'
        ].iloc[0]
        empty_spaces = self.stations[self.stations["station_no"] == station_no][
            'empty_spaces'
        ].iloc[0]
        return int(available_spaces), int(empty_spaces)

    def find_nearest_stations(self, lat: float, lon: float, top_n: int = 10):
        """
        Find the nearest YouBike stations to the user's location
        :param lat: 使用者的緯度
        :param lon: 使用者的經度
        :param top_n: 返回最近的站點數量
        :return: DataFrame 包含最近的站點
        """
        # 創建一個stations數據框的淺拷貝
        stations_copy = self.stations.copy()

        # 計算使用者與每個站點之間的距離
        stations_copy['distance'] = stations_copy.apply(
            lambda row: get_distance(lat, lon, float(row['lat']), float(row['lng'])),
            axis=1,
        )

        # 過濾掉不正確的日期時間字符串
        def is_valid_datetime(date_str):
            try:
                pd.to_datetime(date_str, errors='raise')
                return True
            except:
                return False

        stations_copy = stations_copy[stations_copy['time'].apply(is_valid_datetime)]

        # 將time轉換為標準的時間格式
        stations_copy['time'] = pd.to_datetime(stations_copy['time'], errors='coerce')

        # 計算距現在的時間差，並格式化為幾小時幾分鐘前
        stations_copy['time'] = pd.Timestamp.now() - stations_copy['time']
        stations_copy['time'] = stations_copy['time'].apply(
            lambda x: (
                (
                    f"{x.seconds // 3600}小時 {x.seconds % 3600 // 60}分鐘前"
                    if x.seconds // 3600 > 0
                    else f"{x.seconds // 60}分鐘前"
                )
                if pd.notnull(x)
                else "未知"
            )
        )

        # 找到最近的n個站點
        nearest_stations = stations_copy.nsmallest(top_n, 'distance')

        return nearest_stations[
            [
                'station_no',
                'name_tw',
                'address_tw',
                'distance',
                'available_spaces',
                'empty_spaces',
                'time',
                'lat',
                'lng',
            ]
        ]


if __name__ == "__main__":
    youbike = YouBike()
    pprint(youbike.find_nearest_stations(22.62617, 120.28624))
