import pathlib
import re

import tinydb.operations
from tinydb import TinyDB, Query
from tqdm import tqdm

from constants import DocType


def add_to_purchases(item):
    def transform(doc):
        doc["purchase_ids"].append(item)

    return transform


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


class Database(object):
    def __init__(self, path: str = "downloaderDB.json"):
        self.__path = path
        self.__db = TinyDB(self.__path)

    def get_creators(self):
        return self.__db.search(Query().type == DocType.CREATOR_PAGE)

    def get_library(self, creator_id: str) -> list:
        """
        Retrieves a list of items from the library based on the provided creator ID.

        :param creator_id: The unique identifier of the creator.
        :type creator_id: str
        :return: A list of products from the library that were created by the specified creator.
        :rtype: list
        """
        q = Query()
        items = self.__db.search((q.creator_id == creator_id)
                                 & (q.type == DocType.LIBRARY_PAGE))
        return items

    def update_library(self, response: dict) -> None:
        results = response["results"]
        creators = response["creators"]
        # insert new creators
        for creator in tqdm(creators, desc='Processing creators'):
            if not self.__db.contains((Query().creator_id == creator["id"]) & (Query().type == DocType.CREATOR_PAGE)):
                self.__db.insert({"creator_id": creator["id"],
                                  "name": creator["name"],
                                  "purchase_ids": [],
                                  "type": DocType.CREATOR_PAGE})
                tqdm.write(f"{creator['name']}[{creator['id']}] inserted in creator page")
        with tqdm(total=len(results), desc='Processing results', dynamic_ncols=True) as pbar:
            for result in results:
                product_info: dict = result["product"]
                name: str = product_info["name"]
                creator_id: str = product_info["creator_id"]
                purchase_info: dict = result["purchase"]
                purchase_id: str = purchase_info["id"]
                download_url: str = purchase_info["download_url"]
                product = {"name": name, "creator_id": creator_id, "purchase_id": purchase_id,
                           "download_url": download_url, "type": DocType.LIBRARY_PAGE}
                pbar.set_description(f"Updating {product['name']}".ljust(50))
                # update creator page if purchase id is not already in there
                self.__db.update(add_to_purchases(purchase_id),
                                 (Query()["type"] == DocType.CREATOR_PAGE)
                                 & (Query()["creator_id"] == creator_id)
                                 & (~(Query().purchase_ids.any(purchase_id))))
                # update library page
                self.__db.upsert(product,
                                 (Query()['purchase_id'] == purchase_id) & (Query()['type'] == DocType.LIBRARY_PAGE))
                pbar.update()

    def update_products(self, response: dict, creator_id: str) -> None:
        raw_title = response["purchase"]["product_name"]
        title = sanitize_title(raw_title)
        content_items: dict = response['content']['content_items']
        purchase: dict = response["purchase"]
        purchase_id: str = purchase["id"]
        product = {"content": content_items,
                   "purchase_id": purchase_id,
                   "creator_id": creator_id,
                   "name": title,
                   "type": DocType.PRODUCT_PAGE}

        self.__db.upsert(product,
                         (Query()['purchase_id'] == purchase_id) & (Query()['type'] == DocType.PRODUCT_PAGE))

    def get_library_pages(self, creator_id: str) -> list:
        return self.__db.search((Query()['creator_id'] == creator_id) & (Query()['type'] == DocType.LIBRARY_PAGE))

    def get_product_pages(self, creator_id: str) -> list:
        return self.__db.search((Query()['creator_id'] == creator_id) & (Query()['type'] == DocType.PRODUCT_PAGE))
