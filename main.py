import download_manager
import config

if __name__ == '__main__':
    c = config.Config()
    dm = DownloadManager.DownloadManager(c)
    dm.download_all()


