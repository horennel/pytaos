from server.tdengine import TdEngine

if __name__ == '__main__':
    connect = TdEngine(host='localhost', port=6041, db='test', username='root', password='taosdata', timeout=10)
    resp = connect.execute('select * from mtpt_cldwxx_202110111646401 order by ts desc limit 1')
    print(resp)
