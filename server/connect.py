import requests
from requests.auth import HTTPBasicAuth

from server.model import Model


class Connect(object):
    def __init__(self, host='localhost', port=6041, username='root', password='taosdata', timeout=10):
        self._rest_url = 'http://%s:%d/rest/sql' % (host, port)
        self._auth = HTTPBasicAuth(username, password)
        self._timeout = timeout

    def execute(self, sql: str):
        sql = self._parse_sql(sql)
        resp = self._request(sql)
        return resp

    def _parse_sql(self, sql: str):
        return sql.encode('gbk')

    def _request(self, sql: bytes):
        resp = requests.post(url=self._rest_url, data=sql, auth=self._auth, timeout=self._timeout)
        model = Model(resp.text)
        return model
