# pytaos

The separate `server.iotdb.IoTDB` client provides access to Apache IoTDB without changing the existing API.

## Install

```sh
python -m pip install -r requirements.txt
```

## IoTDB

The client supports IoTDB 2.x Tree REST v2 and Table REST v1. It uses HTTP
Basic authentication and applies the configured request timeout.

```python
import os
from server.iotdb import IoTDB

# Tree model: write fully qualified root paths in SQL.
tree = IoTDB(host="127.0.0.1", port=18080, username=os.environ["IOTDB_USERNAME"],
             password=os.environ["IOTDB_PASSWORD"], model="tree")
rows = tree.execute("SELECT temperature FROM root.factory.room LIMIT 10")

# Table model: the configured database is sent with Table REST requests.
table = IoTDB(host="127.0.0.1", port=18080, db="weather",
              username=os.environ["IOTDB_USERNAME"], password=os.environ["IOTDB_PASSWORD"], model="table")
rows = table.execute("SELECT * FROM readings LIMIT 10")
table.execute("INSERT INTO readings(time, site, temperature) VALUES (1, 'north', 12.5)")
```

`query(sql, database=None, row_limit=1000)` returns a pandas DataFrame.
`non_query(sql, database=None)` returns IoTDB's success response. `execute`
routes `SELECT`, `SHOW`, `DESCRIBE`, `DESC`, `LIST`, and `EXPLAIN` statements to
`query`; other statements go to `non_query`. Tree query results include IoTDB's
`timestamps` as a leading `Time` column. Table query results use the returned
`column_names` and rows.

Table requests use `/rest/table/v1/query` and `/rest/table/v1/nonQuery`, and
include `database` when configured. Tree requests use `/rest/v2/query` and
`/rest/v2/nonQuery`; Tree SQL should refer to full paths such as
`root.factory.room.temperature`. REST v2 must be enabled on the IoTDB server.

Offline IoTDB tests use a
mocked HTTP transport and need no running database:

```sh
python -m unittest discover -s tests -v
```
