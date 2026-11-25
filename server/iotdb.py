import re

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth


class IoTDBError(RuntimeError):
    """Raised when IoTDB returns an HTTP or SQL error."""


class IoTDB(object):
    def __init__(
        self,
        host='localhost',
        port=18080,
        db=None,
        username='root',
        password='root',
        timeout=10,
        model='tree',
        scheme='http',
    ):
        model = model.lower()
        scheme = scheme.lower()
        if model not in ('tree', 'table'):
            raise ValueError("model must be 'tree' or 'table'")
        if scheme not in ('http', 'https'):
            raise ValueError("scheme must be 'http' or 'https'")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError('port must be an integer between 1 and 65535')
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError('timeout must be positive')

        host = host.strip()
        if not host:
            raise ValueError('host must not be empty')
        if ':' in host and not host.startswith('['):
            host = '[%s]' % host

        self._model = model
        self._database = db
        self._rest_url = '%s://%s:%d%s' % (
            scheme,
            host,
            port,
            '/rest/v2' if model == 'tree' else '/rest/table/v1',
        )
        self._auth = HTTPBasicAuth(username, password)
        self._timeout = timeout

    def query(self, sql, database=None, row_limit=1000):
        """Run a query and return a pandas DataFrame."""
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError('sql must not be empty')
        if not isinstance(row_limit, int) or row_limit < 1:
            raise ValueError('row_limit must be a positive integer')

        payload = {'sql': sql, 'row_limit': row_limit}
        selected_database = self._database if database is None else database
        if self._model == 'table' and selected_database:
            payload['database'] = selected_database
        result = self._request('query', payload)
        return self._to_dataframe(result)

    def non_query(self, sql, database=None):
        """Run a statement that does not return a row set."""
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError('sql must not be empty')

        payload = {'sql': sql}
        selected_database = self._database if database is None else database
        if self._model == 'table' and selected_database:
            payload['database'] = selected_database
        return self._request('nonQuery', payload)

    def execute(self, sql, database=None):
        """Route SQL to query/nonQuery and return a DataFrame or success object."""
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError('sql must not be empty')
        if re.match(r'^(SELECT|SHOW|DESCRIBE|DESC|LIST|EXPLAIN)\b', sql.lstrip(), re.I):
            return self.query(sql, database=database)
        return self.non_query(sql, database=database)

    def _request(self, action, payload):
        try:
            response = requests.post(
                url='%s/%s' % (self._rest_url, action),
                json=payload,
                auth=self._auth,
                timeout=self._timeout,
            )
        except requests.RequestException as error:
            raise IoTDBError('IoTDB request failed: %s' % error) from error

        try:
            body = response.json()
        except ValueError as error:
            raise IoTDBError('IoTDB returned invalid JSON (HTTP %s)' % response.status_code) from error

        if response.status_code < 200 or response.status_code >= 300:
            message = body.get('message') if isinstance(body, dict) else None
            raise IoTDBError('IoTDB HTTP %s: %s' % (response.status_code, message or response.text))
        if not isinstance(body, dict):
            raise IoTDBError('IoTDB returned an invalid response object')

        code = body.get('code')
        if code is not None:
            try:
                success = int(code) == 200
            except (TypeError, ValueError):
                success = False
            if not success:
                raise IoTDBError('IoTDB %s: %s' % (code, body.get('message', 'SQL execution failed')))
        return body

    def _to_dataframe(self, body):
        values = body.get('values', [])
        if not isinstance(values, list):
            raise IoTDBError('IoTDB returned an invalid values field')

        if self._model == 'table':
            columns = body.get('column_names')
            if not isinstance(columns, list) or not all(isinstance(name, str) for name in columns):
                raise IoTDBError('IoTDB Table response is missing column_names')
            if any(not isinstance(row, list) or len(row) != len(columns) for row in values):
                raise IoTDBError('IoTDB Table response row width does not match column_names')
            return pd.DataFrame(values, columns=columns)

        expressions = body.get('expressions') or []
        columns = expressions if expressions else body.get('column_names')
        if not isinstance(columns, list) or not all(isinstance(name, str) for name in columns):
            raise IoTDBError('IoTDB Tree response is missing result columns')
        if any(not isinstance(column, list) for column in values):
            raise IoTDBError('IoTDB Tree response values must be column-oriented')
        if len(values) != len(columns):
            raise IoTDBError('IoTDB Tree response column count does not match values')

        row_count = len(values[0]) if values else 0
        if any(len(column) != row_count for column in values):
            raise IoTDBError('IoTDB Tree response columns have different lengths')
        rows = [list(row) for row in zip(*values)] if values else []
        if expressions:
            timestamps = body.get('timestamps')
            if not isinstance(timestamps, list) or len(timestamps) != row_count:
                raise IoTDBError('IoTDB Tree response has invalid timestamps')
            columns = ['Time'] + columns
            rows = [[timestamps[index]] + row for index, row in enumerate(rows)]
        return pd.DataFrame(rows, columns=columns)
