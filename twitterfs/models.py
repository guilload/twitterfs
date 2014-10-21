import cStringIO
import urllib2

from PIL import Image

import arrow
import tweepy


def prettify(string, colorize=True):
    lst = []
    pos = 0

    for word in string.split(' '):

        if pos + len(word) > 79:
            word = '\n' + word
            pos = 0

        pos += len(word) + 1  # + 1 for whitespaces...

        if colorize:
            if word.startswith('@'):
                word = '\x1b[1;34m{}\x1b[0m'.format(word)

            if word.startswith('http'):
                word = '\x1b[4m{}\x1b[0m'.format(word)

        lst.append(word)

    return ' '.join(lst)


class Status(tweepy.Status):

    template = '\n'.join(['-' * 79,
                          '\x1b[1m{name}\x1b[0m \x1b[37m@{screen_name} {timeago}\x1b[0m\n',
                          '{text}\n',
                          'Retweet  Favorites',
                          '{retweet_count:<10}{favorite_count}\n'])

    @property
    def timeago(self):
        timeago = arrow.get(self.created_at).humanize()
        length = 79 - len(self.author.name) - len(self.author.screen_name) -  3
        return timeago.rjust(length, ' ')

    def __str__(self):
        return self.template.format(name=self.author.name,
                                    screen_name=self.author.screen_name,
                                    timeago=self.timeago,
                                    text=prettify(self.text),
                                    retweet_count=self.retweet_count,
                                    favorite_count=self.favorite_count)


class User(tweepy.User):

    template = '\n'.join(['{picture}',
                          '{name}',
                          '{handle}',
                          '{location}\n',
                          '{description}\n\n',
                          '                         tweets  following  followers',
                          '                         {statuses_count:<8}{friends_count:<11}{followers_count}\n',
                          '{user_timeline}\n'])

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self._home_timeline = []
        self._picture = None
        self._user_timeline = []

        self._last_refreshed = arrow.utcnow().replace(seconds=-120)

    def __str__(self):
        return self.template.format(picture=self.picture,
                                    name=self.center(self.name),
                                    handle=self.center(self.handle),
                                    location=self.center(self.location),
                                    description=self.pretty_description,
                                    statuses_count=self.statuses_count,
                                    friends_count=self.friends_count,
                                    followers_count=self.followers_count,
                                    user_timeline=self.user_timeline)

    @staticmethod
    def asciify(url):
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        stream = cStringIO.StringIO(response.read())

        img = Image.open(stream)
        width, height = img.size
        width, height = 79, int(height * 79. / width)
        img = img.resize((width, height))
        pixel = img.load()
        colors = '@%#*+=-:. '

        chars = []
        for h in xrange(height):
            for w in xrange(width):
                rgb = pixel[w, h]
                chars.append(colors[int(sum(rgb) / 3.0 / 256.0 * 10) % len(colors)])  # FIXME
            chars.append('\n')

        return ''.join(chars)

    def center(self, string):
        length = 39 + len(string) / 2
        return string.rjust(length, ' ')

    def friends_ids(self, *args, **kargs):
        return self._api.friends_ids(user_id=self.id, *args, **kargs)

    # The two following properties can't be set in __init__, because
    # screen_name does not exist at that stage

    @property
    def handle(self):
        return '@{}'.format(self.screen_name)

    @property
    def path(self):
        return '/{}'.format(self.handle)

    @property
    def picture(self):
        if not self._picture:
            url = self.profile_image_url.replace('_normal', '')
            self._picture = self.asciify(url)
        return self._picture

    @property
    def pretty_description(self):
        if len(self.description) > 79:
            return prettify(self.description, colorize=False)
        else:
            return self.center(self.description)

    def refresh_user_timeline(self):
        if self._last_refreshed < arrow.utcnow().replace(seconds=-120):
            since_id = self._user_timeline[0].id if self._user_timeline else None
            statuses = self._api.user_timeline(self.id, since_id=since_id)
            statuses.extend(self._user_timeline)
            self._user_timeline = statuses
            self._last_refreshed = arrow.utcnow()

    def refresh_home_timeline(self):
        since_id = self._home_timeline[0].id if self._home_timeline else None
        statuses = self._api.home_timeline(since_id=since_id)
        statuses.extend(self._home_timeline)
        self._home_timeline = statuses

    def refresh_timelines(self):
        for func in (self.refresh_user_timeline, self.refresh_home_timeline):
            func()

    @property
    def user_timeline(self):
        return ''.join(str(st) for st in self._user_timeline)

    utimeline = user_timeline

    @property
    def home_timeline(self):
        return ''.join(str(st) for st in reversed(self._home_timeline))

    htimeline = home_timeline
