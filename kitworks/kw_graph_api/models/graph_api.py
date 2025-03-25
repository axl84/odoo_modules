import logging
import requests

_logger = logging.getLogger(__name__)


class FacebookGraphApi:
    graph_url = 'https://graph.facebook.com'

    @staticmethod
    def headers():
        return {'Content-Type': 'application/json',
                'accept': 'application/json', }

    def get_url(self, ext=''):
        url = self.graph_url + '{}'.format(ext)
        return url

    def make_request(self, method, url, body=None, params=None, headers=None):
        headers = headers or self.headers()
        # pylint: disable=E8106
        response = requests.request(
            method=method, url=self.get_url(url), params=params,
            json=body, headers=headers, )
        try:
            data = response.json()
        except Exception as e:
            _logger.debug(e)
            return {'error': e}
        if 200 <= response.status_code < 300:
            return {'data': data}
        return {'error': data}

    def get(self, url, params=None, headers=None):
        return self.make_request(
            'get', url=url, params=params, headers=headers)

    def post(self, url, body=None, headers=None):
        return self.make_request(
            'post', url=url, body=body, headers=headers)

    def get_facebook_graph(self, url='', params=None, headers=None):
        return self.get(url=url, params=params, headers=headers)

    def post_facebook_graph(self, url='', body=None, headers=None):
        return self.post(url=url, body=body, headers=headers)
