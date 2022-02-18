import json


class Model(object):
    def __init__(self, text):
        kwargs = json.loads(text)
        status = kwargs.get('status')
        self.status = 'success' if status == 'succ' else status
        code = kwargs.get('code')
        self.code = code if code else 200
        self.desc = kwargs.get('desc')
        self.head = kwargs.get('head')
        self.column_meta = kwargs.get('column_meta')
        self.data = kwargs.get('data')
        self.rows = kwargs.get('rows')
