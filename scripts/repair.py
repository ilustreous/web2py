# -*- coding: utf-8 -*-
import os

def main():
    """
    written by Kacper Krupa
    re-creates app folders if they are missing
    (such as when web2py donwloaded from a GIT repository)
    """
    for app in os.listdir('applications'):
        path = os.path.join('applications', app)
        if os.path.isdir(path):
            dirs = [x for x in os.listdir(path) \
                    if os.path.isdir(os.path.join(path, x))]
            for d in ['sessions', 'errors', 'databases', 'tests', 'uploads', 
                      'cache', 'languages', 'private', 'cron']:
                if not d in dirs:
                    os.mkdir(os.path.join(path, d))

if __name__ == '__main__':
    main()
