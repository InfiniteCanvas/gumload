import json
import os


class Config(dict):
    """Simple Config class that extends dict."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with open('config.json') as f:
            data = json.load(f)

        self.update(data)

        if 'only_specified_creators' not in self:
            self['only_specified_creators'] = True
        if 'match_size_using_content_info' not in self:
            self['match_size_using_content_info'] = True
        if 'threads' not in self:
            self['threads'] = 1
        if 'refresh' not in self:
            self['refresh'] = True
        if 'folder' not in self:
            self['folder'] = os.getcwd()
        if 'db_path' not in self:
            self['db_path'] = "downloaderDB.json"
        if 'user_agent' not in self:
            self['user_agent'] = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0"
