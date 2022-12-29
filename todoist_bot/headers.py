"""Create a headers dictionary for requests to the Todoist sync API.

Call this once and pass the functions that call the SYNC API.

:author: Shay Hill
:created: 2022-12-28
"""


from requests.structures import CaseInsensitiveDict

SYNC_URL = "https://api.todoist.com/sync/v9/sync"


def new_headers(api_key: str) -> CaseInsensitiveDict[str]:
    """Create a new headers dictionary for requests to the Todoist sync API.

    :param api_key: The API key for the Todoist account.
    :return: A dictionary of headers for requests to the Todoist sync API.
    """
    headers: CaseInsensitiveDict[str] = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = "Bearer " + api_key
    return headers
