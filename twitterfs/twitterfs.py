import os
import sys
import threading
import time

reload(sys)
sys.setdefaultencoding('utf-8')

import tweepy

from fuse import FUSE, LoggingMixIn, Operations

from .conf import conf
from .fs import DIR_555, DIR_755, FILE_444, FILE_644, FS
from .models import Status, User


tweepy.ModelFactory.status = Status
tweepy.ModelFactory.user = User


class TwitterFS(LoggingMixIn, Operations):

    def __init__(self):
        self._api = self.setup_api()
        self._me = self._api.me()
        self._fs = self.setup_fs()
        self._users = self.setup_users()

        self._refresh_rate = 120
        self._thread = self.setup_thread()

    def setup_api(self):
        consumer_key = conf.get('twitter', 'consumer_key')
        consumer_secret = conf.get('twitter', 'consumer_secret')
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

        access_token = conf.get('twitter', 'access_token')
        access_token_secret = conf.get('twitter', 'access_token_secret')
        auth.set_access_token(access_token, access_token_secret)

        return tweepy.API(auth)

    def setup_fs(self):
        dirs = (('/followers', DIR_555),
                ('/following', DIR_755),
                ('/timeline', FILE_444),
                (self._me.path, FILE_644))

        fs = FS()
        for path, mode in dirs:
            fs[path] = {'st_mode': mode}

        return fs

    def setup_users(self):
        users = {}

        follower_ids = set(self._me.followers_ids())
        following_ids = set(self._me.friends_ids())
        user_ids = follower_ids | following_ids

        for user in self._api.lookup_users(user_ids=user_ids):
            for root, mode, ids in (('/followers', FILE_444, follower_ids),
                                    ('/following', FILE_644, following_ids)):
                if user.id in ids:
                    path = os.path.join(root, user.handle)
                    self._fs[path] = {'st_mode': mode}
                    users[path] = user

        return users

    def setup_thread(self):
        thread = threading.Thread(target=self.refresh)
        thread.daemon = True
        thread.start()
        return thread

    def refresh(self):
        while True:
            self._me.refresh_timelines()

            self._fs['/timeline'].st_size = len(self._me.htimeline)
            self._fs[self._me.path].st_size = len(self._me.utimeline)

            time.sleep(self._refresh_rate)

    @staticmethod
    def spawn(target, *args):
        """
        Calls to twitter's API are slow, so let's trigger them in a thread
        and give the user the sensation of instantaneity. Yes... this is a bit
        ugly but... it works!
        """
        threading.Thread(target=target, args=args).start()

    def follow(self, path):
        if path not in self._fs:
            _, handle = os.path.split(path)
            self._fs[path] = {'st_mode': FILE_644}
            self._users[path] = self._api.create_friendship(handle)

    def unfollow(self, path):
        if path in self._fs:
            root, handle = os.path.split(path)
            self._api.destroy_friendship(handle)

            del self._fs[root]._children[handle]
            del self._users[path]

    def create(self, path, mode):
        if path.startswith('/following/@'):
            self.spawn(self.follow, path)

    def getattr(self, path, fh):
        return self._fs[path].stat()

    def read(self, path, size, offset, fh):
        if path == self._me.path:
            data = self._me.user_timeline
            self._fs[path].st_size = len(data)
            return data[offset:offset + size]

        if path.startswith(('/followers/@', '/following/@')):
            user = self._users[path]
            user.refresh_user_timeline()
            data = str(user)
            self._fs[path].st_size = len(data)
            return data[offset:offset + size]

        if path == '/timeline':
            data = self._me.home_timeline
            self._fs[path].st_size = len(data)
            return data[offset:offset + size]

    def readdir(self, path, fh):
        return ['.', '..'] + self._fs[path].ls()

    def unlink(self, path):
        if path.startswith('/following/@'):
            self.spawn(self.unfollow, path)

    def truncate(self, path, length, fh=None):
        pass

    def write(self, path, data, offset, fh):
        if path == self._me.path:
            self.spawn(self._api.update_status, data)
            return len(data)
