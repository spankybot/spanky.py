import requests
import time


class RequestData():
    def __init__(self, request, content):
        self._request = request
        self.content = content

    @property
    def status_code(self):
        return self._request.status_code


def fetch_url(url, timeout_sec=30, max_size=1024*1024*20):
    """
    Fetch data from an url with a timeout and maximum size
    """
    req = requests.get(url, stream=True)
    try:
        req.raise_for_status()

        size = 0
        start = time.time()

        content = bytes()
        # Get a chunk
        for chunk in req.iter_content(1024 * 1024):
            # If download time exceeds the given timeout, exit
            if time.time() - start > timeout_sec:
                print("Image %s took too long to download" % url)
                raise TimeoutError("Timeout error downloading %s" % url)

            content += chunk
            size += len(chunk)

            # If the size eceeds the given maximum size, exit
            if size > max_size:
                print("Image %s is too large" % url)
                raise PermissionError("Image too large")
    except:
        return RequestData(req, None)

    return RequestData(req, content)
