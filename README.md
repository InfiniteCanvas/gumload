# GumLoad

Downloads your library from gumroad.

Clone this repository, install requirements, setup config.json and run it.

## Config

The config looks like this:

```json
{
  "threads": 5,
  "only_specified_creators": false,
  "match_size_using_content_info": true,
  "db_path": "gumload.json",
  "refresh": true,
  "folder": "J:\\My Drive\\Gumroad",
  "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
  "_gumroad_app_session": "your app session",
  "_gumroad_guid": "your guid",
  "creators": [
    {
      "id": "000000",
      "name": "optional name"
    }
  ]
}
```

Config options:

- ``threads``: number of connections for fetching pages and downloading items
- ``only_specified_creators``: if you have creators specified in the ``creators`` section, only those will get
  downloaded
- ``match_size_using_content_info``: if true, checks file sizes it gets from the product page. if false, matches it from
  the header data from the download request
- ``db_path``: where the database is stored (just a huge ass json file)
- ``refresh``: instead of using the data stored in the database, fetches it from the internet
- ``folder``: folder where all the things are getting stored
- ``userAgent``: user agent used for sending requests
- ``_gumroad_app_session``: find your app session value from your cookies
- ``_gumroad_guid``: find your guid from your cookies

With everything configured you should be able to run it with ``python .\main.py`` (this is windows).

It only downloads whatever hasn't been downloaded or does not match the size it should have.