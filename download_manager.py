import concurrent.futures
import json
import os
import queue
import threading
from functools import partial

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

import constants
from config import Config
from database import Database
from constants import DEFAULT_USER_AGENT, BASE_URL, LIBRARY_URL, ComponentType


class DownloadManager:
    class DownloadSession(requests.Session):
        def __init__(self,
                     app_session: str,
                     guid: str,
                     user_agent: str = DEFAULT_USER_AGENT) -> None:
            super().__init__()
            self.cookies.set("_gumroad_app_session", app_session)
            self.cookies.set("_gumroad_guid", guid)
            self.headers["User-Agent"] = user_agent

        def get_soup(self, url: str) -> BeautifulSoup:
            response = self.get(url, allow_redirects=False)
            response.raise_for_status()
            return BeautifulSoup(response.content, "lxml")

    def __init__(self, config: Config):
        self.__db = Database(config['db_path'])
        self.__db_lock = threading.Lock()
        self.__config = config
        self.__semaphore = threading.Semaphore(config['threads'])
        self.__sessions = queue.Queue(maxsize=(config['threads']))
        for _ in range(config['threads']):
            self.__sessions.put(DownloadManager.DownloadSession(config["_gumroad_app_session"],
                                                                config["_gumroad_guid"],
                                                                config["user_agent"]))

    @staticmethod
    def __load_json_data(soup: BeautifulSoup, data_component_name: constants.ComponentType) -> dict:
        """
        Load JSON data from a BeautifulSoup object.

        :param soup: The BeautifulSoup object containing HTML or XML data.
        :param data_component_name: The value of the "data-component-name" attribute used to identify the script element containing the JSON data.
        :return: A dictionary representing the parsed JSON data.
        """
        script = soup.find("script",
                           attrs={
                               "class": "js-react-on-rails-component",
                               "data-component-name": str(data_component_name),
                           })
        return json.loads(script.string)

    def __update_library(self) -> None:
        # fetch data from constants.LIBRARY_URL
        tqdm.write("Updating Library...")
        with self.__semaphore:
            try:
                session = self.__sessions.get()
                soup = session.get_soup(LIBRARY_URL)
                json_data = self.__load_json_data(soup, ComponentType.LIBRARY_PAGE)
                self.__db.update_library(json_data)
                self.__sessions.put(session)

            except Exception as e:
                tqdm.write(f'Failed to update library due to [{e}]')

    def __update_all_products(self) -> None:
        for creator in self.__db.get_creators():
            self.__update_products(creator["creator_id"], creator["name"])

    def __update_products(self, creator_id: str, creator_name: str = None) -> None:
        tqdm.write(f"Updating Product List of {creator_name if creator_name else creator_id}...")
        products = self.__db.get_library_pages(creator_id)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            f = partial(self.__update_product, creator_id)
            executor.map(f, products)

    def __update_product(self, creator_id: str, product: dict):
        with self.__semaphore:
            session = self.__sessions.get()
            try:
                soup = session.get_soup(product['download_url'])
                json_data = self.__load_json_data(soup, ComponentType.DOWNLOAD_PAGE_WITH_CONTENT)
                with self.__db_lock:
                    self.__db.update_products(json_data, creator_id)

            except Exception as e:
                tqdm.write(f'Failed to update products of [{creator_id}] due to [{e}]')
            finally:
                self.__sessions.put(session)

    def download_all(self) -> None:
        if self.__config["refresh"]:
            self.__update_library()
            for creator in self.__config["creators"]:
                self.__update_products(creator["id"], creator["name"])

        download_tasks = []
        for creator in self.__config['creators']:
            creator_id = creator['id']
            products = self.__db.get_product_pages(creator_id)
            print(f"Downloading everything from {creator['name']}[{creator_id}]")
            creator_folder = os.path.join(self.__config["folder"], creator['name'])
            for product in products:
                for content in product['content']:
                    product_path = f"{os.path.join(creator_folder, product['name'], content['file_name'])}.{content['extension']}"
                    download_url = BASE_URL + content['download_url']
                    download_tasks.append({"path": product_path, "url": download_url, "name": product['name']})

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.__download_product, download_tasks)

    def __download_product(self, download_task: dict) -> None:
        with self.__semaphore:
            session = self.__sessions.get()
            try:
                tqdm.write(f"Processing product {download_task['name']}")
                path = download_task['path']
                name = download_task['name']
                response = session.get(download_task['url'], stream=True)
                response.raise_for_status()
                os.makedirs(os.path.dirname(path), exist_ok=True)
                total_size = int(response.headers.get('content-length', 0))
                tqdm.write(
                    f"Downloading product {download_task['name']}[{total_size / 1024 / 1024:.2f} MB] to {download_task['path']}")

                if os.path.exists(path) and os.path.getsize(path) == total_size:
                    tqdm.write(f"File [{name}] already downloaded and size matches, skipping download.")
                    return

                # Either file does not exist or size does not match, proceed with download
                with open(path, 'wb') as file, tqdm(
                        leave=False,
                        desc=name,
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        dynamic_ncols=True
                ) as bar:
                    for data in response.iter_content(chunk_size=4096):
                        if data:
                            size = file.write(data)
                            bar.update(size)

                    tqdm.write(f'Successfully downloaded [{name}]')
            except Exception as e:
                tqdm.write(f'Failed to download {download_task["name"]}[{download_task["url"]}] due to {e}')
            finally:
                self.__sessions.put(session)
