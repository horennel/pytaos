from server.connect import Connect

if __name__ == '__main__':
    conn = Connect()
    resp = conn.execute('show databases')
    print(resp.data)

    resp = conn.execute('create database demo')
    print(resp.status, resp.data, resp.desc)

    resp = conn.execute('show databases')
    print(resp.data)
