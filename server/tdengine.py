import json
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth


class TdEngine(object):
    def __init__(self, host='localhost', port=6041, db='test', username='root', password='taosdata', timeout=10):
        self._rest_url = 'http://%s:%d/rest/sql/%s' % (host, port, db)
        self._auth = HTTPBasicAuth(username, password)
        self._timeout = timeout

    def execute(self, sql: str):
        resp = self._request(sql.encode('utf-8'))
        return resp

    def _request(self, sql: bytes):
        resp = requests.post(url=self._rest_url, data=sql, auth=self._auth, timeout=self._timeout)
        return self._parse(resp)

    @staticmethod
    def _parse(response):
        result = json.loads(response.text)
        if result.get('status') != 'succ':
            raise Exception(result.get('desc'))
        return pd.DataFrame(data=result['data'], columns=result['head'])
