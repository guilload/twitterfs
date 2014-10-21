# twitterfs

## install

```sh
$ git clone git@github.com:guilload/twitterfs.git
$ pip install install -r requirements --allow-external PIL --allow-unverified PIL
```

*PIL needs JPEG and zlib support (see [here](http://jj.isgeek.net/2011/09/install-pil-with-jpeg-support-on-ubuntu-oneiric-64bits/))*

## configuration

```
[twitter]
consumer_key: <consumer key>
consumer_secret: <consumer secret>

access_token: <access token>
access_token_secret: <access token secret>
```

## mount
```sh
$ mkdir <mounpoint>
$ bin/twitterfs <mounpoint>
```

## use
```sh
$ cd <mounpoint>
$ echo "Tweeting from my file system based twitter client!" > @myprofile
$ cat @myprofile
$ cat timeline
$ ls following/
$ ls followers/
$ touch following/@BarackObama
$ cat following/@BarackObama
$ rm following/@BarackObama
```
