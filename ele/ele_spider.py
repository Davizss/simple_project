# !/usr/bin/env python
# -*- coding:utf-8 -*-
# 本文件的作用：饿了吗外卖店铺爬虫
from geopy.geocoders import Nominatim  # pip install geopy
import geohash2  # pip install geohash2
import requests
import json
from jsonpath import jsonpath
import argparse


class EleShop(object):
    # 位置周边的店铺url
    detail_url = 'https://www.ele.me/restapi/shopping/restaurants?extras%5B%5D=activities&geohash={}&latitude={}&limit=24&longitude={}&offset={}&terminal=web'
    # 获取关键字 位置信息的url
    keyword_url = 'https://www.ele.me/restapi/v2/pois?extras%5B%5D=count&geohash={}&keyword={}&limit=20&type=nearby'
    # 登陆之后的cookie
    cookie = {
        'ubt_ssid': '2rel6g7ydbnsbysyelhwrorwrigoa4qt_2018-12-07',
        'utrace': 'eb0897c2ecec2b1a6a4bb0ca5b89d5d5_2018-12-07',
        'perf_ssid': 'yt6hdzzzq1qq6c6t3yyrr2pry27k9tn6_2018-12-10',
        'PASSPORT_ACCOUNT_ID': '5080465000026878608',
        'PASSPORT_TOKEN': 'PBE_1.0_befc610e751bac8895d3a306138316c3f7f51fefaa0c52f4264540de5eb8fab88fd5cd1aaa45a8421d65f39fad7e362bc27b7350738805870c396c5f6e18052509a000039ee6191684afb62c959267fc2b8e4b9474a9d1aa435644ef9b1e5b7afaff2c3752b9a5dd6a0cfcfa86ed476e86c71fdc25d90b0363294006cfaddeac83dbe57fe5433ae753f76c1a762d1f02abe64c2cd75933cc817c0eae3e030c84a278dcf64691480d45a5026ce7fb9e959cd69584d1b0a287ce199b03bc3bf44f',
        'cna': 'ZYZ5EzdP1AkCAT0yYrpAbXD2',
        'track_id': '1544499764|e9e4fb0b7f4e1fd5fea97e62401d2118a7575cc6dabb2e30ba|130d1a1eccebe22da2358ae36734c57e',
        'USERID': '4995639218',
        'SID': 'VUcZAZuNV4GVqLeVKcOS6mKzFPUhetSJHq5g',
        'isg': 'BA8PVtcjjwncAYv0AjGXYlsUnqXZnGpwW_-TmiEcJH6F8CryOAeapCzh9iDOiDvO',
    }

    def __init__(self, keyword, city='上海', page=30):
        self.keyword = keyword
        self.city = city
        self.page = int(page)

    def start(self):
        if not self.keyword:
            raise ValueError("Keyword parameters cannot be empty")
        # 获取城市的geohash
        location = {'city': self.city}
        city_info = self.find_detail_location_info(location)
        city_geohash = city_info['geohash']
        # 通过关键字构建 位置url 得到位置信息
        keyword_url = self.keyword_url.format(city_geohash, self.keyword)
        keyword_geohash, lat, lon = self.get_keyword_info(keyword_url)
        # 根据page构建detail_url,发起请求并解析获得数据
        for i in range(self.page):
            detail_url = self.detail_url.format(keyword_geohash, lat, lon, i*24)
            res = requests.get(detail_url, cookies=self.cookie)
            res = json.loads(res.text)
            for detail in res:
                # 店铺活动
                activities = jsonpath(detail, '$.activities..description')
                if activities:
                    activities = list(set(activities))
                else:
                    activities = []
                # 最近订单量
                order_num = detail['recent_order_num']
                # 评价
                rating = detail['rating']
                # 店铺名
                name = detail['name']
                item = {
                    'name': name,
                    'order_num': order_num,
                    'activities': activities,
                    'rating': rating
                }
                print(item)

    def get_keyword_info(self, url):
        """
        请求关键字url, 返回第一个数据的geohash及经纬度
        :param url: 构建好的关键字url
        :return: 请求结果的第一个数据的geohash及经纬度
        """
        res = requests.get(url)
        res = json.loads(res.text)
        # 关键字 的位置geohash
        keyword_geohash = res[0]['geohash']
        # 位置的 经纬度
        lat = float('%.5f' % res[0]['latitude'])
        lon = float('%.5f' % res[0]['longitude'])
        return keyword_geohash, lat, lon

    def find_detail_location_info(self, location):
        """
        根据location信息, 获取改location的经纬度及geohash
        :param location: 要查询的location信息
        :return: loc_info 字典
        """
        geolocator = Nominatim()
        try:
            location = geolocator.geocode(location, timeout=5)
            if location:
                lat = float('%.5f' % location.latitude)
                lon = float('%.5f' % location.longitude)
                encode = geohash2.encode(lat, lon)
                loc_info = {
                    'location': location,
                    'lat': lat,
                    'lon': lon,
                    'geohash': encode
                }
                return loc_info
        except Exception as e:
            print(e)
            return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keyword', '-k', type=str, required=True, help='要查询的位置的关键字')
    parser.add_argument('--city', '-c', type=str, required=False, default='上海', help='要查询的城市名')
    parser.add_argument('--page', '-p', type=int, required=False, default=30, help='返回的商家列表页的页数,默认30页,最多30页')

    args = parser.parse_args()
    ele = EleShop(keyword=args.keyword, city=args.city, page=args.page)
    ele.start()