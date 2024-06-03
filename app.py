import datetime
import os
from pprint import pprint, pformat

from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, LocationMessageContent
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    FlexMessage,
    FlexCarousel,
)
from linebot.v3.messaging.models import TextMessage, FlexBubble, FlexCarousel
from linebot.v3.messaging.models.uri_action import URIAction
from linebot.v3.messaging.models.message_action import MessageAction

import pandas as pd
import requests

import flex_message
from utils.google import GoogleMaps
from utils.youbike import YouBike


class LineBotApp:
    def __init__(self):
        load_dotenv()
        self.app = Flask(__name__)
        self.line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

        self.handler = WebhookHandler(self.line_channel_secret)
        self.configuration = Configuration(
            host='https://api.line.me', access_token=self.line_channel_access_token
        )

        self.google_maps = GoogleMaps(api_key=self.google_maps_api_key)
        self.youbike = YouBike()

        self.setup_routes()
        self.setup_handlers()

    def setup_routes(self):
        @self.app.route("/callback", methods=['POST'])
        def callback():
            signature = request.headers['X-Line-Signature']
            body = request.get_data(as_text=True)

            try:
                self.handler.handle(body, signature)
            except InvalidSignatureError:
                abort(400)

            return 'OK'

    def setup_handlers(self):
        # 處理文字訊息
        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_message(event):
            user_message = event.message.text

            if user_message == "美食":
                response = "請分享您的位置資訊，以便我們為您找到附近的美食！"
                self.send_reply(type="text", reply_token=event.reply_token, message=response)
            elif user_message == "YouBike":
                # response = self.get_nearby_youbike()
                response = "請分享您的位置資訊，以便我們為您找到附近的YouBike！"
                self.send_reply(type="text", reply_token=event.reply_token, message=response)
            else:
                self.send_reply(type="text", reply_token=event.reply_token, message="哩洗咧公殺毀")

        # 處理使用者傳送的位置訊息
        @self.handler.add(MessageEvent, message=LocationMessageContent)
        def handel_location_message(event):
            latitude = event.message.latitude
            longitude = event.message.longitude

            gm_response = self.google_maps.get_nearby_restaurants(
                lat=latitude, lon=longitude, top_n=5
            )
            yb_response = self.youbike.find_nearest_stations(lat=latitude, lon=longitude, top_n=5)

            # Google Maps 餐廳訊息
            gm_flex = flex_message.load_json("flex_messages/GoogleMaps.json")
            gm_flex_bubble = FlexBubble.from_dict(gm_flex)
            gm_message = self.get_gm_message(gm_response, gm_flex_bubble)
            gm_flex_carousel = FlexCarousel(contents=gm_message)
            gm_flex_message = FlexMessage(alt_text="Google Maps", contents=gm_flex_carousel)

            self.send_reply(type="flex", reply_token=event.reply_token, message=[gm_flex_message])

    def send_reply(self, type, reply_token, message):
        """
        回覆訊息給使用者
        :param type: str, 訊息類型
        :param reply_token: str, 回覆訊息的 token
        :param message: str or list, 要回覆的訊息內容
        """
        with ApiClient(self.configuration) as api_client:
            if type == "text":
                messaging = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=reply_token, messages=[TextMessage(text=message)]
                )
                try:
                    messaging.reply_message(reply_message_request)
                except Exception as e:
                    self.app.logger.error(f"Error sending message: {e}")
            elif type == "flex":
                messaging = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=reply_token, messages=message
                )
                try:
                    messaging.reply_message(reply_message_request)
                except Exception as e:
                    self.app.logger.error(f"Error sending message: {e}")

    def get_gm_message(self, response: dict, flex_bubble: FlexBubble):
        """
        依據 Google Maps API 回傳的資料，建立 Flex Message

        :param response: dict, Google Maps API 回傳的資料
        :param flex_bubble: FlexBubble, Flex Message 的 Bubble, 作為模板使用
        """

        def get_star_icons(rating: float) -> list:
            """
            依據評分數量，回傳對應的星星圖示

            :param rating: float, 評分數量
            :return: list, 星星圖示的 URL
            """
            gold_star_count = int(rating)
            gray_star_count = 5 - gold_star_count
            star_icons = [
                'https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png'
                for _ in range(gold_star_count)
            ]
            star_icons += [
                'https://developers-resource.landpress.line.me/fx/img/review_gray_star_28.png'
                for _ in range(gray_star_count)
            ]
            return star_icons

        bubbles = []
        for i, restaurant in response.items():
            bubble = flex_bubble.copy(deep=True)

            # 上方圖片
            bubble.hero.url = (
                restaurant["photo"]
                if restaurant["photo"]
                else "https://play-lh.googleusercontent.com/LECOTVlGWVclV1VU3-1YcNoQdF2f37jQaQhX353GkySuwK9EcPXgy92YgKB3QeNvZMXe"
            )
            bubble.hero.action.uri = restaurant["link"]

            # 中間部分
            # 餐廳名稱
            bubble.body.contents[0].text = restaurant["name"]
            # 評分
            stars = get_star_icons(restaurant["rating"])
            for i, star in enumerate(stars):
                bubble.body.contents[1].contents[i].url = star
            bubble.body.contents[1].contents[5].text = str(restaurant["rating"])
            # 距離
            bubble.body.contents[2].contents[0].contents[1].text = f"{restaurant['distance']} 公里"
            # 今日營業時間
            today = datetime.datetime.today().weekday()
            bubble.body.contents[2].contents[1].contents[1].text = (
                restaurant["opening_time"][today]
                if restaurant["opening_time"]
                else "未提供營業時間"
            )

            # 下方按鈕
            bubble.footer.contents[0].action.label = "打開 Google Maps"
            bubble.footer.contents[0].action.uri = restaurant["link"]

            bubbles.append(bubble)

        return bubbles

    def run(self):
        self.app.run(port=8000, host='0.0.0.0', debug=True)


if __name__ == "__main__":
    bot_app = LineBotApp()
    bot_app.run()
