import requests
import json
import hashlib
import time
import re
from mayi_proxy import MaYiProxyMiddleware, UserAgentMiddleware
from jsonpath import jsonpath
import csv
import codecs
import logging


class GetComment(object):
    def __init__(self, c_w=None,):
        self.appkey = "12574478"
        self._m_h5_tk = "ca46b1d6826065873e34f39cd912efbd_1526917063921"
        self._m_h5_tk_enc = "9258d89f8bb06d9204bd4657a9a02dfb"
        self.session = requests.Session()
        jar = requests.cookies.RequestsCookieJar()
        jar.set("_m_h5_tk", self._m_h5_tk, domain=".taobao.com", path="/")
        jar.set("_m_h5_tk_enc", self._m_h5_tk_enc, domain=".taobao.com", path="/")
        self.session.cookies = jar
        self.comment_url = 'http://h5api.m.taobao.com/h5/mtop.taobao.rate.detaillist.get/4.0/?'
        self.answer_url = 'https://acs.m.taobao.com/h5/mtop.taobao.social.feed.aggregate/1.0/?'
        self.next_url = 'https://h5api.m.taobao.com/h5/mtop.taobao.social.ugc.post.detail/2.0/?'
        self.cw = c_w
        self.ab = MaYiProxyMiddleware()
        self.auth, self.proxy = self.ab.get_proxy()
        self.ua = UserAgentMiddleware()

    def getSign(self, ts, data):
        """
        通过淘宝js中的sign规则, 构建sign值
        :return: sign值
        """
        m2 = hashlib.md5()
        str_ = self.getToken() + "&" + str(ts) + "&" + self.appkey + "&" + data
        m2.update(str_.encode('utf-8'))
        return m2.hexdigest()

    def getToken(self):
        """
        获取token值
        :return: token or ''
        """
        _m_h5_tk = self.session.cookies.get("_m_h5_tk")
        if _m_h5_tk is not None:
            token = _m_h5_tk.split("_")[0]
            return token
        return ""

    def getTimeStr(self, timestamp):
        """
        将时间戳转成时间格式
        :param timestamp: 时间戳
        :return: 时间格式
        """
        timestamp = int(timestamp)
        # 转换成localtime
        time_local = time.localtime(timestamp)
        # 转换成新的时间格式(2018-12-05 20:28:54)
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
        return dt

    def get_comment(self, store_id, page=1):
        """
        构建并请求commet_url，并将数据传入到parse_comment函数中解析
        :param store_id: 商品id
        :param page: 页数
        :return:item
        """
        retry = 3
        while retry:
            data = {"auctionNumId": store_id, "rateType": "", "pageSize": 10, "pageNo": page}
            data = json.dumps(data)
            ts = int(time.time() * 1000)
            sign = self.getSign(ts, data)
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
                'Proxy-Authorization': self.auth,
            }
            params = {
                'jsv': '2.4.2',
                'appKey': '12574478',
                't': str(ts),
                'sign': sign,
                'api': 'mtop.taobao.rate.detaillist.get',
                'v': '4.0',
                'ecode': '1',
                'type': 'jsonp',
                'dataType': 'jsonp',
                'AntiCreep': 'true',
                'AntiFlood': 'true',
                'H5Request': 'true',
                'callback': 'mtopjsonp1',
                'data': data
            }
            res = self.session.get(url=self.comment_url, params=params, headers=headers, proxies=self.proxy)
            if 'FAIL_SYS_TOKEN_EXOIRED' in res.text:
                logging.error('过期')
                retry -= 1
            else:
                item = self.parse_comment(res.text)
                return item

    def get_answer(self, store_id):
        """
        构建并请求answer_url，并将数据传入到parse函数中解析
        :param store_id: 商品id
        :return:
        """
        retry = 5
        while retry > 0:
            ua = self.ua.get_ua()
            auth, proxy = self.ab.get_proxy()
            params_str = "{\"refId\":\"%s\",\"namespace\":1,\"pageNum\":1,\"pageSize\":10}" % (store_id)
            data = {"cursor": "1", "pageNum": "1", "pageId": 24501, "env": 1, "bizVersion": 0, "params": params_str}
            data_str = json.dumps(data)
            ts = int(time.time() * 1000)
            sign = self.getSign(ts, data_str)
            params = {
                'appKey': '12574478',
                't': str(ts),
                'sign': sign,
                'api': 'mtop.taobao.social.feed.aggregate',
                'v': '1.0',
                'ecode': '0',
                'timeout': '300000',
                'timer': '300000',
                'AntiCreep': 'true',
                'type': 'jsonp',
                'dataType': 'jsonp',
                'callback': 'mtopjsonp1',
                'data': data_str
            }
            headers = {
                'User-Agent': ua,
                'Proxy-Authorization': auth,
            }
            res = self.session.get(url=self.answer_url, headers=headers, params=params, proxies=proxy)
            if 'FAIL_SYS_TOKEN_EXOIRED' in res.text or 'RGV587_ERROR' in res.text:
                retry -= 1
            else:
                self.parse_answer(res.text)
                return

    def parse_answer(self, response):
        """
        解析网址数据，得到所欲问题类型clusterId，并构建新的anser_url
        """
        response = re.search('mtopjsonp1\((.*)\)', response)
        if response:
            response = json.loads(response.group(1))
            data = jsonpath(response, '$..list')
            if not data:
                return
            data = data[0]
            for i in data:
                for qa in i:
                    if qa['cardType'] == '2':
                        i.pop()
                cluster_id = i[-1]['clusterId']
                answer_id = i[-1]['id']
                params_str = "{\"clusterId\":\"%s\"}" % cluster_id
                self.get_list_answer(answer_id, params_str, find_similar=True)

    def get_list_answer(self, answer_id, params_str, find_similar=True):
        """
        解析网址数据，得到同种问题类型下的所有clusterId，并构建新的anser_url
        """
        ua = self.ua.get_ua()
        auth, proxy = self.ab.get_proxy()
        retry = 3
        while retry > 0:
            data = {"id": "{}".format(answer_id), "params": params_str}
            data_str = json.dumps(data)
            ts = int(time.time() * 1000)
            sign = self.getSign(ts, data_str)
            params = {
                'jsv': '2.4.2',
                'appKey': '12574478',
                't': ts,
                'sign': sign,
                'api': 'mtop.taobao.social.ugc.post.detail',
                'v': '2.0',
                'type': 'jsonp',
                'dataType': 'jsonp',
                'timeout': '20000',
                'AntiCreep': 'true',
                'AntiFlood': 'true',
                'callback': 'mtopjsonp1',
                'data': data_str
            }
            headers = {
                'User-Agent': ua,
                'Proxy-Authorization': auth,
            }
            res = self.session.get(url=self.next_url, headers=headers, params=params, proxies=proxy)
            if 'FAIL_SYS_TOKEN_EXOIRED' in res.text or 'login' in res.text:
                retry -= 1
            else:
                self.parse_list_answer(res.text, find_similar)
                return

    def parse_list_answer(self, response, find_similar):
        """
        解析answert网址，抓取数据并存入到csv中
        """
        response = re.search('mtopjsonp1\((.*)\)', response)
        if response:
            response = json.loads(response.group(1))
            data = jsonpath(response, '$..data')
            if not data:
                return
            data = data[0]
            if find_similar:
                similar_ids = data['similarIds']
                for answer_id in similar_ids:
                    params_str = "{\"pageSize\":10,\"pageNum\":1}"
                    self.get_list_answer(answer_id, params_str, find_similar=False)
            else:
                item = []
                if not data['title']:
                    return
                item.append(data['title'])
                answer = jsonpath(data, '$.list.list..title')
                if len(answer) == 1:
                    answer = ''.join(answer)
                else:
                    answer = '\n'.join([str(answer.index(a) + 1) + '.' + a for a in answer])
                item.append(answer)
                dt = self.getTimeStr(data['gmtCreate'][:-3])
                item.append(dt)

                self.cw.writerow(item)

    def parse_comment(self, response):
        """
        解析comment网址，抓取数据
        :param response: 网页相应
        :return: 无
        """
        response = re.search('mtopjsonp1\((.*)\)', response)
        if response:
            response = json.loads(response.group(1))
            data = jsonpath(response, '$..rateList.*')
            if not data:
                return
            for i in data:
                item = []
                # 商品唯一识别id
                item.append(i['auctionNumId'])
                # 评论用户
                user = jsonpath(i, '$..userNick')
                if user:
                    item.append(user[0])
                else:
                    item.append('Unknown')
                # 评论内容
                appendedFeedback = jsonpath(i, '$..appendedFeedback')
                if appendedFeedback:
                    content = i['feedback'] + '\n' + '买家追评:' + appendedFeedback[0]
                else:
                    content = i['feedback']
                item.append(content)
                # 商品信息
                l = []
                for info in i['skuMap'].items():
                    l.append(':'.join(list(info)))
                item.append(', \n'.join([a for a in l]))
                # 评论发布时间
                item.append(i['feedbackDate'])
                yield item


class SaveToCsv(object):
    """
    将数据存入到csv中
    """
    def save_comment(self, store_id, file_name):
        stu = ['product_id', 'userNick', 'content', 'product_info', 'review_data']
        # 打开文件，追加a
        out = codecs.open(file_name, 'a', encoding='utf-8-sig')
        # 设定写入模式
        csv_write = csv.writer(out, dialect='excel')
        # 写入具体内容
        csv_write.writerow(stu)
        gc = GetComment()
        for page in range(501):
            res = gc.get_comment(store_id=store_id, page=page + 1)
            for item in res:
                csv_write.writerow(item)

    def save_answer(self, store_id, file_name):
        stu = ['question', 'answer', 'question_time']
        out = codecs.open(file_name, 'a', encoding='utf-8-sig')
        # 设定写入模式
        csv_write = csv.writer(out, dialect='excel')
        # 写入具体内容
        csv_write.writerow(stu)
        gc = GetComment(c_w=csv_write)
        gc.get_answer(store_id=store_id)


if __name__ == '__main__':
    sc = SaveToCsv()
    sc.save_answer('44130261582', 'answer.csv')
    sc.save_comment('44130261582', 'answer.csv')
