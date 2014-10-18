import ConfigParser
import os


root = os.path.dirname(__file__)
path = os.path.join(root, 'conf')
conf = ConfigParser.ConfigParser()
conf.read(path)
