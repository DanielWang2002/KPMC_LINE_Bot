import requests
from pprint import pprint

from utils.distance import get_distance


class GoogleMaps:
    def __init__(self, api_key, type_="restaurant", language="zh-TW"):
        self.api_key = api_key
        self.type_ = type_
        self.language = language

    def _get_photo(self, photo_reference: str) -> str:
        url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={self.api_key}"
        response = requests.get(url)
        return response.url

    def _get_details(self, place_id: str) -> dict:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&language={self.language}&key={self.api_key}"
        response = requests.get(url)
        result = response.json().get("result", {})

        phone_number = result.get("formatted_phone_number")
        opening_time = result.get("current_opening_hours", {}).get("weekday_text", [])

        details = {"phone_number": phone_number, "opening_time": opening_time}

        return details

    def get_nearby_restaurants(
        self, lat: float, lon: float, top_n: int, radius: float = 1000
    ) -> dict:
        """
        取得附近餐廳的資訊
        :param lat: float, 緯度
        :param lon: float, 經度
        :param radius: float, 搜尋半徑
        :param top_n: int, 取前 n 筆資料
        """
        location = f"{lat},{lon}"

        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&type={self.type_}&language={self.language}&key={self.api_key}"
        response = requests.get(url)
        results = response.json().get("results", [])

        restaurants = {}

        for i, place in enumerate(results):
            name = place['name']
            rating = place.get('rating', 0)
            place_lat = place['geometry']['location']['lat']
            place_lon = place['geometry']['location']['lng']
            distance = get_distance(lat, lon, place_lat, place_lon)
            place_id = place['place_id']
            photo_ref = (
                place['photos'][0]['photo_reference']
                if 'photos' in place and place['photos']
                else None
            )
            photo_url = self._get_photo(photo_ref) if photo_ref else None

            details = self._get_details(place_id)

            restaurants[i] = {
                "name": name,
                "rating": rating,
                "lat": place_lat,
                "lon": place_lon,
                "distance": distance,
                "link": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                "photo": photo_url,
                **details,
            }

        # 先按照rating排序，再按照距離排序
        return dict(
            sorted(
                restaurants.items(), key=lambda x: (x[1]['rating'], x[1]['distance']), reverse=True
            )[:top_n]
        )
