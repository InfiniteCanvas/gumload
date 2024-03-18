from enum import IntEnum

DEFAULT_USER_AGENT = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0"
BASE_URL = r"https://app.gumroad.com"
LIBRARY_URL = r'https://app.gumroad.com/library'


class DocType(IntEnum):
    LIBRARY_PAGE = 0
    PRODUCT_PAGE = 1
    CREATOR_PAGE = 2


class ComponentType(IntEnum):
    LIBRARY_PAGE = 0
    DOWNLOAD_PAGE_WITH_CONTENT = 1

    def __str__(self):
        if self == ComponentType.LIBRARY_PAGE:
            return "LibraryPage"
        if self == ComponentType.DOWNLOAD_PAGE_WITH_CONTENT:
            return "DownloadPageWithContent"

        return "DEFAULT"
