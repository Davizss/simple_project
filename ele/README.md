# 饿了吗店铺爬虫说明

## 项目依赖库
```bool
pip install geopy
pip install geohash2
pip install jsonpath
```

## ele_spider

### EleShop
EleShop类 可通过城市名、位置关键字及页码,发起请求并解析得到数据

#### 参数
- keyword 要查询的位置的关键字(不可为空)
- city 要查询的城市名,默认上海
- page 返回的商家列表页的页数,默认30页,最多30页

## 使用方法
运行ele_spider.py
```base
 python ele_spider.py -k 位置关键字 -c 城市名 -p 页数
```
