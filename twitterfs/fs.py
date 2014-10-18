import errno
import os
import stat
import time

from fuse import FuseOSError


DIR_555 = stat.S_IFDIR | 0555
DIR_755 = stat.S_IFDIR | 0755
FILE_444 = stat.S_IFREG | 0444
FILE_644 = stat.S_IFREG | 0644


class Node(object):

    def __init__(self, st_mode, st_atime=None, st_ctime=None, st_mtime=None,
                 st_nlink=1, st_size=0, root='/', name='/'):

        now = time.time()

        self.st_atime = st_atime or now
        self.st_ctime = st_ctime or now
        self.st_mode = st_mode
        self.st_mtime = st_mtime or now
        self.st_nlink = st_nlink
        self.st_size = st_size

        self.root = root
        self.name = name
        self.path = os.path.join(self.root, self.name)

        self._children = {}

    def __contains__(self, path):
        try:
            self[path]
            return True
        except FuseOSError:
            return False

    def __getitem__(self, path):
        if path == '/':
            return self

        tree = self.tree(path)
        head, tail = tree[1], '/{}'.format('/'.join(tree[2:]))

        try:
            return self._children[head][tail]
        except KeyError:
            raise FuseOSError(errno.ENOENT)

    def __setitem__(self, path, kwargs):
        tree = self.tree(path)

        if len(tree) == 2:
            head, tail = tree[0], tree[1]
            self._children[tail] = Node(root=self.path, name=tail, **kwargs)
        else:
            head, tail = tree[1], '/{}'.format('/'.join(tree[2:]))

            try:
                self._children[head][tail] = kwargs
            except KeyError:
                raise FuseOSError(errno.ENOENT)

    def ls(self):
        return self._children.keys()

    def rm(self, path):
        try:
            del self._children[path]
        except KeyError:
            raise FuseOSError(errno.ENOENT)

    def stat(self):
        return dict(st_mode=self.st_mode, st_atime=self.st_atime,
                    st_ctime=self.st_ctime, st_mtime=self.st_mtime,
                    st_nlink=self.st_nlink, st_size=self.st_size)

    @staticmethod
    def tree(path):
        """
        >>> Node.tree('/')
        ['/']
        >>> Node.tree('/foo')
        ['/', 'foo']
        """
        if path == '/':
            return ['/']

        lst = ['/']
        lst.extend(path.strip('/').split('/'))
        return lst


FS = lambda: Node(st_mode=DIR_755, st_nlink=2)  # root node
