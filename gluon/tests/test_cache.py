'''
    Unit tests for gluon.cache
'''

import unittest
from gluon.storage import Storage
from gluon.cache import CacheInRam, CacheOnDisk

class TestCache(unittest.TestCase):
    def testCacheInRam(self):
        #defaults to mode='http'
        cache = CacheInRam() 
        self.assertEqual(cache('a',lambda:1,0), 1)
        self.assertEqual(cache('a',lambda:2,100), 1)
        cache.clear('b')
        self.assertEqual(cache('a',lambda:2,100), 1)
        cache.clear('a')
        self.assertEqual(cache('a',lambda:2,100), 2)
        cache.clear()
        self.assertEqual(cache('a',lambda:3,100), 3)
        self.assertEqual(cache('a',lambda:4,0), 4)
    def testCacheOnDisk(self):
        #defaults to mode='http'
        s=Storage({'application':'admin','folder':'applications/admin'})
        cache = CacheOnDisk(s) 
        self.assertEqual(cache('a',lambda:1,0), 1)
        self.assertEqual(cache('a',lambda:2,100), 1)
        cache.clear('b')
        self.assertEqual(cache('a',lambda:2,100), 1)
        cache.clear('a')
        self.assertEqual(cache('a',lambda:2,100), 2)
        cache.clear()
        self.assertEqual(cache('a',lambda:3,100), 3)
        self.assertEqual(cache('a',lambda:4,0), 4)


if __name__ == "__main__":
    unittest.main()
    
