import json
import urllib.request
from urllib.error import HTTPError, URLError


class Request:
    def __init__(self, url):
        self.url = url
        self.response = None

    def send(self):
        """
        :return: полученный от сервиса json
        """
        try:
            with urllib.request.urlopen(self.url) as result:
                self.response = result.read().decode('utf8')
        except (HTTPError, URLError) as e:
            print('Error during http request')
        self._parse_response()
        return self.response

    def _parse_response(self):
        if self.response:
            try:
                self.response = json.loads(self.response)
            except Exception as e:
                self.response = None

