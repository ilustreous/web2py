#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    Unit tests for IS_URL()
"""

import sys
import os
sys.path.append(os.path.realpath('../'))

import unittest
from validators import *
import validators

# ##############################################################################


class TestIsUrl(unittest.TestCase):

    def testModeHttp(self):

        # defaults to mode='http'

        x = IS_URL()
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80',
                         None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # explicit use of 'http' mode

        x = IS_URL(mode='http')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80',
                         None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # prepends 'https' instead of 'http'

        x = IS_URL(mode='http', prepend_scheme='https')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('https://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('https://google.ca:80',
                         None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # prepending disabled

        x = IS_URL(prepend_scheme=None)
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # custom allowed_schemes

        x = IS_URL(mode='http', allowed_schemes=[None, 'http'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('https://google.ca'), ('https://google.ca',
                         'invalid url!'))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80',
                         None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # custom allowed_schemes, excluding None

        x = IS_URL(allowed_schemes=['http'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('https://google.ca'), ('https://google.ca',
                         'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca:80'), ('google.ca:80',
                         'invalid url!'))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # custom allowed_schemes and prepend_scheme

        x = IS_URL(allowed_schemes=[None, 'https'],
                   prepend_scheme='https')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         'invalid url!'))
        self.assertEqual(x('https://google.ca'), ('https://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('https://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('https://google.ca:80',
                         None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg',
                         'invalid url!'))

        # Now any URL requiring prepending will fail, but prepending is still enabled!

        x = IS_URL(allowed_schemes=['http'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))

    def testModeGeneric(self):

        # 'generic' mode

        x = IS_URL(mode='generic')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80',
                         None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal',
                         'invalid url!'))

        # 'generic' mode with custom allowed_schemes that still includes 'http' (the default for prepend_scheme)

        x = IS_URL(mode='generic', allowed_schemes=['http', 'blargg'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca',
                         'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca:80'), ('google.ca:80',
                         'invalid url!'))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal',
                         None))

        # 'generic' mode with overriden prepend_scheme

        x = IS_URL(mode='generic', prepend_scheme='ftp')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca',
                         None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('ftp://google.ca:80',
                         None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal',
                         'invalid url!'))

        # 'generic' mode with overriden allowed_schemes and prepend_scheme

        x = IS_URL(mode='generic', allowed_schemes=[None, 'ftp', 'ftps'
                   ], prepend_scheme='ftp')
        self.assertEqual(x('http://google.ca'), ('http://google.ca',
                         'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca',
                         None))
        self.assertEqual(x('google.ca:80'), ('ftp://google.ca:80',
                         None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal',
                         'invalid url!'))

        # Now any URL requiring prepending will fail, but prepending is still enabled!

        x = IS_URL(mode='generic', allowed_schemes=['http'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))

    def testExceptionalUse(self):

        # mode must be in set ['http', 'generic']

        try:
            x = IS_URL(mode='ftp')
            x('http://www.google.ca')
        except Exception, e:
            if str(e) != "mode='ftp' is not valid":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid mode: 'ftp'")

        # allowed_schemes in 'http' mode must be in set [None, 'http', 'https']

        try:
            x = IS_URL(allowed_schemes=[None, 'ftp', 'ftps'],
                       prepend_scheme='ftp')
            x('http://www.benn.ca')  # we can only reasonably know about the error at calling time
        except Exception, e:
            if str(e)\
                 != "allowed_scheme value 'ftp' is not in [None, 'http', 'https']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid allowed_schemes: [None, 'ftp', 'ftps']"
                      )

        # prepend_scheme's value must be in allowed_schemes (default for 'http' mode is [None, 'http', 'https'])

        try:
            x = IS_URL(prepend_scheme='ftp')
            x('http://www.benn.ca')  # we can only reasonably know about the error at calling time
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='ftp' is not in allowed_schemes=[None, 'http', 'https']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'ftp'")

        # custom allowed_schemes that excludes 'http', so prepend_scheme must be specified!

        try:
            x = IS_URL(allowed_schemes=[None, 'https'])
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='http' is not in allowed_schemes=[None, 'https']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'http'")

        # prepend_scheme must be in allowed_schemes

        try:
            x = IS_URL(allowed_schemes=[None, 'http'],
                       prepend_scheme='https')
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='https' is not in allowed_schemes=[None, 'http']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'https'")

        # prepend_scheme's value (default is 'http') must be in allowed_schemes

        try:
            x = IS_URL(mode='generic', allowed_schemes=[None, 'ftp',
                       'ftps'])
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='http' is not in allowed_schemes=[None, 'ftp', 'ftps']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'http'")

        # prepend_scheme's value must be in allowed_schemes, which by default is all schemes that really exist

        try:
            x = IS_URL(mode='generic', prepend_scheme='blargg')
            x('http://www.google.ca')  # we can only reasonably know about the error at calling time
        except Exception, e:
            if not str(e).startswith("prepend_scheme='blargg' is not in allowed_schemes="
                    ):
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'blargg'")

        # prepend_scheme's value must be in allowed_schemes

        try:
            x = IS_URL(mode='generic', allowed_schemes=[None, 'http'],
                       prepend_scheme='blargg')
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='blargg' is not in allowed_schemes=[None, 'http']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'blargg'")

        # Not inluding None in the allowed_schemes essentially disabled prepending, so even though
        # prepend_scheme has the invalid value 'http', we don't care!

        x = IS_URL(allowed_schemes=['https'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))

        # Not inluding None in the allowed_schemes essentially disabled prepending, so even though
        # prepend_scheme has the invalid value 'http', we don't care!

        x = IS_URL(mode='generic', allowed_schemes=['https'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))


# ##############################################################################


class TestIsGenericUrl(unittest.TestCase):

    x = validators.IS_GENERIC_URL()

    def testInvalidUrls(self):
        urlsToCheckA = []
        for i in range(0, 32) + [127]:

            # Control characters are disallowed in any part of a URL

            urlsToCheckA.append('http://www.benn' + chr(i) + '.ca')

        urlsToCheckB = [
            None,
            '',
            'http://www.no spaces allowed.com',
            'http://www.benn.ca/no spaces allowed/',
            'http://www.benn.ca/angle_<bracket/',
            'http://www.benn.ca/angle_>bracket/',
            'http://www.benn.ca/invalid%character',
            'http://www.benn.ca/illegal%%20use',
            'http://www.benn.ca/illegaluse%',
            'http://www.benn.ca/illegaluse%0',
            'http://www.benn.ca/illegaluse%x',
            'http://www.benn.ca/ill%egaluse%x',
            'http://www.benn.ca/double"quote/',
            'http://www.curly{brace.com',
            'http://www.benn.ca/curly}brace/',
            'http://www.benn.ca/or|symbol/',
            'http://www.benn.ca/back\slash',
            'http://www.benn.ca/the^carat',
            'http://left[bracket.me',
            'http://www.benn.ca/right]bracket',
            'http://www.benn.ca/angle`quote',
            '-ttp://www.benn.ca',
            '+ttp://www.benn.ca',
            '.ttp://www.benn.ca',
            '9ttp://www.benn.ca',
            'ht;tp://www.benn.ca',
            'ht@tp://www.benn.ca',
            'ht&tp://www.benn.ca',
            'ht=tp://www.benn.ca',
            'ht$tp://www.benn.ca',
            'ht,tp://www.benn.ca',
            'ht:tp://www.benn.ca',
            'htp://invalid_scheme.com',
            ]

        failures = []

        for url in urlsToCheckA + urlsToCheckB:
            if self.x(url)[1] == None:
                failures.append('Incorrectly accepted: ' + str(url))

        if len(failures) > 0:
            self.fail(failures)

    def testValidUrls(self):
        urlsToCheck = [
            'ftp://ftp.is.co.za/rfc/rfc1808.txt',
            'gopher://spinaltap.micro.umn.edu/00/Weather/California/Los%20Angeles'
                ,
            'http://www.math.uio.no/faq/compression-faq/part1.html',
            'mailto:mduerst@ifi.unizh.ch',
            'news:comp.infosystems.www.servers.unix',
            'telnet://melvyl.ucop.edu/',
            'hTTp://www.benn.ca',
            '%66%74%70://ftp.is.co.za/rfc/rfc1808.txt',
            '%46%74%70://ftp.is.co.za/rfc/rfc1808.txt',
            '/faq/compression-faq/part1.html',
            'google.com',
            'www.google.com:8080',
            '128.127.123.250:8080',
            'blargg:ping',
            'http://www.benn.ca',
            'http://benn.ca',
            'http://amazon.com/books/',
            'https://amazon.com/movies',
            'rtsp://idontknowthisprotocol',
            'HTTP://allcaps.com',
            'http://localhost',
            'http://localhost#fragment',
            'http://localhost/hello',
            'http://localhost/hello?query=True',
            'http://localhost/hello/',
            'http://localhost:8080',
            'http://localhost:8080/',
            'http://localhost:8080/hello',
            'http://localhost:8080/hello/',
            'file:///C:/Documents%20and%20Settings/Jonathan/Desktop/view.py'
                ,
            ]

        failures = []

        for url in urlsToCheck:
            if self.x(url)[1] != None:
                failures.append('Incorrectly rejected: ' + str(url))

        if len(failures) > 0:
            self.fail(failures)

    def testPrepending(self):
        self.assertEqual(self.x('google.ca'), ('google.ca', None))  # Does not prepend scheme for abbreviated domains
        self.assertEqual(self.x('google.ca:8080'), ('google.ca:8080',
                         None))  # Does not prepend scheme for abbreviated domains
        self.assertEqual(self.x('https://google.ca'),
                         ('https://google.ca', None))  # Does not prepend when scheme already exists

        # Does not prepend if None type is not specified in allowed_scheme, because a scheme is required

        y = validators.IS_GENERIC_URL(allowed_schemes=['http', 'blargg'
                ], prepend_scheme='http')
        self.assertEqual(y('google.ca'), ('google.ca', 'invalid url!'))


# ##############################################################################


class TestIsHttpUrl(unittest.TestCase):

    x = validators.IS_HTTP_URL()

    def testInvalidUrls(self):
        urlsToCheck = [
            None,
            '',
            'http://invalid' + chr(2) + '.com',
            'htp://invalid_scheme.com',
            'blargg://invalid_scheme.com',
            'http://-123.com',
            'http://abcd-.ca',
            'http://-abc123-.me',
            'http://www.dom&ain.com/',
            'http://www.dom=ain.com/',
            'http://www.benn.ca&',
            'http://%62%65%6E%6E%2E%63%61/path',
            'http://.domain.com',
            'http://.domain.com./path',
            'http://domain..com',
            'http://domain...at..com',
            'http://domain.com..',
            'http://domain.com../path',
            'http://domain.3m',
            'http://domain.-3m',
            'http://domain.3m-',
            'http://domain.-3m-',
            'http://domain.co&m',
            'http://domain.m3456',
            'http://domain.m-3/path#fragment',
            'http://domain.m---k/path?query=value',
            'http://23.32..',
            'http://23..32.56.0',
            'http://38997.222.999',
            'http://23.32.56.99.',
            'http://.23.32.56.99',
            'http://.23.32.56.99.',
            'http://w127.123.0.256:8080',
            'http://23.32.56.99:abcd',
            'http://23.32.56.99:23cd',
            'http://google.com:cd22',
            'http://23.32:1300.56.99',
            'http://www.yahoo:1600.com',
            'path/segment/without/starting/slash',
            'http://www.math.uio.no;param=3',
            '://ABC.com:/%7esmith/home.html',
            ]

        failures = []

        for url in urlsToCheck:
            if self.x(url)[1] == None:
                failures.append('Incorrectly accepted: ' + str(url))

        if len(failures) > 0:
            self.fail(failures)

    def testValidUrls(self):

        urlsToCheck = [
            'http://abc.com:80/~smith/home.html',
            'http://ABC.com/%7Esmith/home.html',
            'http://ABC.com:/%7esmith/home.html',
            'http://www.math.uio.no/faq/compression-faq/part1.html',
            '//google.ca/faq/compression-faq/part1.html',
            '//google.ca/faq;param=3',
            '//google.ca/faq/index.html?query=5',
            '//google.ca/faq/index.html;param=value?query=5',
            '/faq/compression-faq/part1.html',
            '/faq;param=3',
            '/faq/index.html?query=5',
            '/faq/index.html;param=value?query=5',
            'google.com',
            'benn.ca/init/default',
            'benn.ca/init;param=value/default?query=value',
            'http://host-name---with-dashes.me',
            'http://www.host-name---with-dashes.me',
            'http://a.com',
            'http://a.3.com',
            'http://a.bl-ck.com',
            'http://bl-e.b.com',
            'http://host123with456numbers.ca',
            'http://1234567890.com.',
            'http://1234567890.com./path',
            'http://google.com./path',
            'http://domain.xn--0zwm56d',
            'http://127.123.0.256',
            'http://127.123.0.256/document/drawer',
            '127.123.0.256/document/',
            '156.212.123.100',
            'http://www.google.com:180200',
            'http://www.google.com:8080/path',
            'http://www.google.com:8080',
            '//www.google.com:8080',
            'www.google.com:8080',
            'http://127.123.0.256:8080/path',
            '//127.123.0.256:8080',
            '127.123.0.256:8080',
            'http://example.me??query=value?',
            'http://a.com',
            'http://3.com',
            'http://www.benn.ca',
            'http://benn.ca',
            'http://amazon.com/books/',
            'https://amazon.com/movies',
            'hTTp://allcaps.com',
            'http://localhost',
            'HTTPS://localhost.',
            'http://localhost#fragment',
            'http://localhost/hello;param=value',
            'http://localhost/hello;param=value/hi;param2=value2;param3=value3'
                ,
            'http://localhost/hello?query=True',
            'http://www.benn.ca/hello;param=value/hi;param2=value2;param3=value3/index.html?query=3'
                ,
            'http://localhost/hello/?query=1500&five=6',
            'http://localhost:8080',
            'http://localhost:8080/',
            'http://localhost:8080/hello',
            'http://localhost:8080/hello%20world/',
            'http://www.a.3.be-nn.5.ca',
            'http://www.amazon.COM',
            ]

        failures = []

        for url in urlsToCheck:
            if self.x(url)[1] != None:
                failures.append('Incorrectly rejected: ' + str(url))

        if len(failures) > 0:
            self.fail(failures)

    def testPrepending(self):
        self.assertEqual(self.x('google.ca'), ('http://google.ca',
                         None))  # prepends scheme for abbreviated domains
        self.assertEqual(self.x('google.ca:8080'),
                         ('http://google.ca:8080', None))  # prepends scheme for abbreviated domains
        self.assertEqual(self.x('https://google.ca'),
                         ('https://google.ca', None))  # does not prepend when scheme already exists

        y = validators.IS_HTTP_URL(prepend_scheme='https')
        self.assertEqual(y('google.ca'), ('https://google.ca', None))  # prepends https if asked

        z = validators.IS_HTTP_URL(prepend_scheme=None)
        self.assertEqual(z('google.ca:8080'), ('google.ca:8080', None))  # prepending disabled

        try:
            validators.IS_HTTP_URL(prepend_scheme='mailto')
        except Exception, e:
            if str(e)\
                 != "prepend_scheme='mailto' is not in allowed_schemes=[None, 'http', 'https']":
                self.fail('Wrong exception: ' + str(e))
        else:
            self.fail("Got invalid prepend_scheme: 'mailto'")

        # Does not prepend if None type is not specified in allowed_scheme, because a scheme is required

        a = validators.IS_HTTP_URL(allowed_schemes=['http'])
        self.assertEqual(a('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(a('google.ca:80'), ('google.ca:80',
                         'invalid url!'))


# ##############################################################################

if __name__ == '__main__':
    unittest.main()

