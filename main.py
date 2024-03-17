import queue
import requests
from bs4 import BeautifulSoup
import json
import re
import pathlib
import concurrent.futures
import os
from tqdm import tqdm  # import tqdm
import threading

with open('config.json') as f:
    _config = json.load(f)

# Use a semaphore to limit the number of concurrent downloads
_threads = _config['threads']
_semaphore = threading.Semaphore(_threads)
_sessions = queue.Queue(maxsize=_threads)


def download_file(local_task: dict):
    file_url = local_task['url']
    path = local_task['path']
    current_file_name = local_task['file']

    with _semaphore:
        try:
            if _sessions.empty():
                _sessions.put(GumroadSession(_config["_gumroad_app_session"],
                                             _config["_gumroad_guid"],
                                             _config["userAgent"]))
            session = _sessions.get()
            response = session.get(file_url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(path), exist_ok=True)
            total = int(response.headers.get('content-length', 0))
            tqdm.write(f"Downloading {current_file_name} [{total / 1024 / 1024:.2f} MB]")

            # Check if file exists and size matches total size
            if os.path.exists(path) and os.path.getsize(path) == total:
                tqdm.write('File already downloaded and size matches, skipping download.')
                _sessions.put(session)
                return  # Skip the file download as it already exists with exact size

            # Either file does not exist or size does not match, process with download
            with open(path, 'wb') as file, tqdm(
                    leave=False,
                    desc=current_file_name,
                    total=total,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(chunk_size=4096):
                    if data:
                        size = file.write(data)
                        bar.update(size)

            print(f'Successfully downloaded {current_file_name}[{file_url}]')
            _sessions.put(session)
        except Exception as e:
            tqdm.write(f'Failed to download {current_file_name}[{file_url}] due to {e}')


def start_downloads(download_tasks: list):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(download_file, download_tasks)


def get_download_urls(html_response):
    # Parse the HTML
    soup = BeautifulSoup(html_response, 'html.parser')

    # Find the creator by name
    creator_name = "Reine"  # Specify the creator's name you want to filter for
    creator_div = soup.find('div', text=creator_name)

    # If the creator is found, find and store any buttons saying "Download"
    download_buttons = []
    if creator_div:
        for button in creator_div.find_all('button'):
            if 'Download' in button.get_text():
                download_buttons.append(button.get_text())

    # Print the download buttons
    print("Download buttons associated with creator", creator_name, ":", download_buttons)


def _load_json_data(soup: BeautifulSoup, data_component_name: str) -> dict:
    script = soup.find(
        "script",
        attrs={
            "class": "js-react-on-rails-component",
            "data-component-name": data_component_name,
        },
    )
    return json.loads(script.string)


class GumroadSession(requests.Session):
    def __init__(self, app_session: str, guid: str, user_agent: str) -> None:
        super().__init__()

        self.cookies.set("_gumroad_app_session", app_session)
        self.cookies.set("_gumroad_guid", guid)
        self.headers["User-Agent"] = user_agent

    @property
    def base_url(self) -> str:
        return "https://app.gumroad.com"

    def get_soup(self, url: str) -> BeautifulSoup:
        response = self.get(url, allow_redirects=False)
        response.raise_for_status()
        return BeautifulSoup(response.content, "lxml")


# default creator id is foxy
def get_products(requested_creator_id="3515733564687"):
    url = 'https://app.gumroad.com/library'

    # Use get_soup method to get the parsed HTML
    soup = gumroad_session.get_soup(url)

    json_content = _load_json_data(soup, "LibraryPage")

    # Create the dict
    creator_download_dict = {}
    for result in json_content['results']:
        creator_id = result['product']['creator_id']
        download_url = result['purchase']['download_url']

        if creator_id in creator_download_dict:
            creator_download_dict[creator_id].append(download_url)
        else:
            creator_download_dict[creator_id] = [download_url]

    return creator_download_dict[requested_creator_id]


def sanitize_title(raw_title: str) -> str:
    """
    Function to sanitize string to work as part of a path.

    Args:
        title[str]: input string (title)

    Returns:
        A sanitized string
    """
    raw_title = raw_title.strip()  # remove leading and trailing white spaces
    # replace invalid filename characters with underscore
    raw_title = re.sub(r'[\\/*?:"<>|]', '_', raw_title)
    raw_title = pathlib.PurePath(raw_title).name
    return raw_title


def get_product_info(product_urls: list) -> dict:
    product_download_urls = {}
    for _url in product_urls:
        soup = gumroad_session.get_soup(_url)
        script = _load_json_data(soup, "DownloadPageWithContent")
        raw_title = script['purchase']['product_name']
        sanitized_title = sanitize_title(raw_title)
        print(f"Processing {sanitized_title}")
        for _item in script['content']['content_items']:
            _file_name = f'{_item["file_name"]}.{_item["extension"]}'
            _url = f"{gumroad_session.base_url}{_item['download_url']}"
            if sanitized_title in product_download_urls:
                product_download_urls[sanitized_title][_file_name] = _url
            else:
                product_download_urls[sanitized_title] = {_file_name: _url}
    return product_download_urls


_download_tasks = []

if __name__ == '__main__':
    with open('config.json') as f:
        _config = json.load(f)
    gumroad_session = GumroadSession(_config["_gumroad_app_session"],
                                     _config["_gumroad_guid"],
                                     _config["userAgent"])

    for creator in _config["creators"]:
        creator_name = creator["name"]
        if "folder" in _config:
            creator_folder = os.path.join(str(_config["folder"]), creator_name)
        else:
            creator_folder = os.path.join(os.getcwd(), creator_name)
        print(f"Saving to {creator_folder}")
        product_pages = get_products(creator["id"])
        download_urls = get_product_info(product_pages)
        print(f"Downloading {creator_name} products [{len(product_pages)}]")

        for title, files in download_urls.items():
            title_folder = os.path.join(creator_folder, title)
            print(title)

            for file_name, url in files.items():
                print(f" - {file_name}")
                file_path = os.path.join(title_folder, file_name)
                _download_tasks.append(
                    {'url': url,
                     'path': file_path,
                     'title': title, 'file': file_name,
                     'creator': creator_name,
                     'creator_folder': creator_folder})

    with open('download_tasks.json', 'w+') as f:
        for task in _download_tasks:
            f.write(json.dumps(task) + '\n')

    start_downloads(_download_tasks)
