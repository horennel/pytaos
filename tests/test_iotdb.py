import unittest
from unittest.mock import Mock, patch

import requests

from server.iotdb import IoTDB, IoTDBError


class IoTDBClientTest(unittest.TestCase):
    def response(self, body, status=200):
        response = Mock()
        response.status_code = status
        response.text = str(body)
        response.json.return_value = body
        return response

    @patch('server.iotdb.requests.post')
    def test_tree_query_decodes_columnar_values_and_timestamps(self, post):
        post.return_value = self.response({
            'code': 200,
            'expressions': ['root.factory.room.temp'],
            'timestamps': [1700000000000, 1700000001000],
            'values': [[21.5, 22.0]],
        })
        client = IoTDB(host='iotdb.local', model='tree')

        result = client.query('SELECT temp FROM root.factory.room')

        self.assertEqual(list(result.columns), ['Time', 'root.factory.room.temp'])
        self.assertEqual(result.values.tolist(), [[1700000000000, 21.5], [1700000001000, 22.0]])
        args, kwargs = post.call_args
        self.assertEqual(args, ())
        self.assertEqual(kwargs['url'], 'http://iotdb.local:18080/rest/v2/query')
        self.assertEqual(kwargs['json'], {'sql': 'SELECT temp FROM root.factory.room', 'row_limit': 1000})
        self.assertEqual(kwargs['auth'].username, 'root')
        self.assertEqual(kwargs['timeout'], 10)

    @patch('server.iotdb.requests.post')
    def test_table_query_uses_table_rest_route_database_and_row_values(self, post):
        post.return_value = self.response({
            'column_names': ['time', 'site', 'temperature'],
            'values': [[1700000000000, 'north', 12.5]],
        })
        client = IoTDB(host='127.0.0.1', db='weather', model='table')

        result = client.execute('SELECT * FROM readings')

        self.assertEqual(list(result.columns), ['time', 'site', 'temperature'])
        self.assertEqual(result.iloc[0].tolist(), [1700000000000, 'north', 12.5])
        self.assertEqual(post.call_args.kwargs['url'], 'http://127.0.0.1:18080/rest/table/v1/query')
        self.assertEqual(post.call_args.kwargs['json'], {
            'sql': 'SELECT * FROM readings', 'row_limit': 1000, 'database': 'weather'
        })

    @patch('server.iotdb.requests.post')
    def test_non_query_routes_to_non_query_and_returns_response(self, post):
        body = {'code': 200, 'message': 'success'}
        post.return_value = self.response(body)
        client = IoTDB(model='table', db='weather')

        self.assertEqual(client.execute('INSERT INTO readings(time) VALUES (1)'), body)
        self.assertTrue(post.call_args.kwargs['url'].endswith('/rest/table/v1/nonQuery'))
        self.assertEqual(post.call_args.kwargs['json'], {
            'sql': 'INSERT INTO readings(time) VALUES (1)', 'database': 'weather'
        })

    @patch('server.iotdb.requests.post')
    def test_table_request_can_omit_configured_database(self, post):
        post.return_value = self.response({'code': 200, 'message': 'success'})

        IoTDB(model='table', db='weather').non_query('DROP DATABASE weather', database='')

        self.assertEqual(post.call_args.kwargs['json'], {'sql': 'DROP DATABASE weather'})

    @patch('server.iotdb.requests.post')
    def test_iotdb_sql_errors_are_reported(self, post):
        post.return_value = self.response({'code': 305, 'message': 'no DataRegionGroups'})
        client = IoTDB()

        with self.assertRaisesRegex(IoTDBError, '305: no DataRegionGroups'):
            client.non_query('INSERT INTO root.factory.room(temp) VALUES (1, 21.5)')

    @patch('server.iotdb.requests.post')
    def test_http_errors_include_server_message(self, post):
        post.return_value = self.response({'message': 'unauthorized'}, status=401)

        with self.assertRaisesRegex(IoTDBError, 'HTTP 401: unauthorized'):
            IoTDB().query('SHOW VERSION')

    @patch('server.iotdb.requests.post')
    def test_transport_failures_are_wrapped(self, post):
        post.side_effect = requests.Timeout('timed out')

        with self.assertRaisesRegex(IoTDBError, 'request failed: timed out'):
            IoTDB().query('SHOW VERSION')

    @patch('server.iotdb.requests.post')
    def test_malformed_tree_column_lengths_are_rejected(self, post):
        post.return_value = self.response({
            'expressions': ['s1', 's2'],
            'timestamps': [1],
            'values': [[1], [2, 3]],
        })

        with self.assertRaisesRegex(IoTDBError, 'different lengths'):
            IoTDB().query('SELECT * FROM root.factory.room')

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'model'):
            IoTDB(model='mixed')
        with self.assertRaisesRegex(ValueError, 'port'):
            IoTDB(port=0)


if __name__ == '__main__':
    unittest.main()
