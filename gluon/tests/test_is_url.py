'''
    Unit tests for IS_URL()
'''

import unittest
from gluon.validators import *
import gluon.validators



###############################################################################
class TestIsUrl(unittest.TestCase):
    def testModeHttp(self):
        #defaults to mode='http'
        x = IS_URL() 
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #explicit use of 'http' mode
        x = IS_URL(mode='http')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #prepends 'https' instead of 'http'
        x = IS_URL(mode='http', prepend_scheme='https')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca'), ('https://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('https://google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #prepending disabled
        x = IS_URL(prepend_scheme=None)
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))

        #custom allowed_schemes
        x = IS_URL(mode='http', allowed_schemes=[None, 'http'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('https://google.ca'), ('https://google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #custom allowed_schemes, excluding None
        x = IS_URL(allowed_schemes=['http'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('https://google.ca'), ('https://google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca:80'), ('google.ca:80', 'invalid url!'))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #custom allowed_schemes and prepend_scheme
        x = IS_URL(allowed_schemes=[None, 'https'], prepend_scheme='https')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', 'invalid url!'))
        self.assertEqual(x('https://google.ca'), ('https://google.ca', None))
        self.assertEqual(x('google.ca'), ('https://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('https://google.ca:80', None))
        self.assertEqual(x('unreal.blargg'), ('unreal.blargg', 'invalid url!'))
        
        #Now any URL requiring prepending will fail, but prepending is still enabled!
        x = IS_URL(allowed_schemes=['http'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
    
    
    def testModeGeneric(self):
        #'generic' mode
        x = IS_URL(mode='generic')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('http://google.ca:80', None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal', 'invalid url!'))
        
        #'generic' mode with custom allowed_schemes that still includes 'http' (the default for prepend_scheme)
        x = IS_URL(mode='generic', allowed_schemes=['http', 'blargg'])
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca:80'), ('google.ca:80', 'invalid url!'))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal', None))

        #'generic' mode with overriden prepend_scheme
        x = IS_URL(mode='generic', prepend_scheme='ftp')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca', None))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('google.ca:80'), ('ftp://google.ca:80', None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal', 'invalid url!'))
        
        #'generic' mode with overriden allowed_schemes and prepend_scheme
        x = IS_URL(mode='generic', allowed_schemes=[None, 'ftp', 'ftps'], prepend_scheme='ftp')
        self.assertEqual(x('http://google.ca'), ('http://google.ca', 'invalid url!'))
        self.assertEqual(x('google.ca'), ('google.ca', None))
        self.assertEqual(x('ftp://google.ca'), ('ftp://google.ca', None))
        self.assertEqual(x('google.ca:80'), ('ftp://google.ca:80', None))
        self.assertEqual(x('blargg://unreal'), ('blargg://unreal', 'invalid url!'))
        
        #Now any URL requiring prepending will fail, but prepending is still enabled!
        x = IS_URL(mode='generic', allowed_schemes=['http'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))
        
    
    def testExceptionalUse(self):
        #mode must be in set ['http', 'generic']
        try:
            x = IS_URL(mode='ftp')
            x('http://www.google.ca')
        except Exception, e:
            if str(e) != "mode='ftp' is not valid":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid mode: 'ftp'")
        
        #allowed_schemes in 'http' mode must be in set [None, 'http', 'https']
        try:
            x = IS_URL(allowed_schemes=[None, 'ftp', 'ftps'], prepend_scheme='ftp')
            x('http://www.benn.ca') #we can only reasonably know about the error at calling time
        except Exception, e:
            if str(e) != "allowed_scheme value 'ftp' is not in [None, 'http', 'https']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid allowed_schemes: [None, 'ftp', 'ftps']")
        
        #prepend_scheme's value must be in allowed_schemes (default for 'http' mode is [None, 'http', 'https'])
        try:
            x = IS_URL(prepend_scheme='ftp')
            x('http://www.benn.ca') #we can only reasonably know about the error at calling time
        except Exception, e:
            if str(e) != "prepend_scheme='ftp' is not in allowed_schemes=[None, 'http', 'https']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'ftp'")

        #custom allowed_schemes that excludes 'http', so prepend_scheme must be specified!
        try:
            x = IS_URL(allowed_schemes=[None, 'https'])
        except Exception, e:
            if str(e) != "prepend_scheme='http' is not in allowed_schemes=[None, 'https']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'http'")
            
        #prepend_scheme must be in allowed_schemes
        try:
            x = IS_URL(allowed_schemes=[None, 'http'], prepend_scheme='https')
        except Exception, e:
            if str(e) != "prepend_scheme='https' is not in allowed_schemes=[None, 'http']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'https'")

        #prepend_scheme's value (default is 'http') must be in allowed_schemes
        try:
            x = IS_URL(mode='generic', allowed_schemes=[None, 'ftp', 'ftps'])
        except Exception, e:
            if str(e) != "prepend_scheme='http' is not in allowed_schemes=[None, 'ftp', 'ftps']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'http'")
        
        #prepend_scheme's value must be in allowed_schemes, which by default is all schemes that really exist
        try:
            x = IS_URL(mode='generic', prepend_scheme='blargg')
            x('http://www.google.ca') #we can only reasonably know about the error at calling time
        except Exception, e:
            if not str(e).startswith("prepend_scheme='blargg' is not in allowed_schemes="):
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'blargg'")
            
        #prepend_scheme's value must be in allowed_schemes
        try:
            x = IS_URL(mode='generic', allowed_schemes=[None, 'http'], prepend_scheme='blargg')
        except Exception, e:
            if str(e) != "prepend_scheme='blargg' is not in allowed_schemes=[None, 'http']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Accepted invalid prepend_scheme: 'blargg'")

        #Not inluding None in the allowed_schemes essentially disabled prepending, so even though
        #prepend_scheme has the invalid value 'http', we don't care!
        x = IS_URL(allowed_schemes=['https'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))

        #Not inluding None in the allowed_schemes essentially disabled prepending, so even though
        #prepend_scheme has the invalid value 'http', we don't care!
        x = IS_URL(mode='generic', allowed_schemes=['https'])
        self.assertEqual(x('google.ca'), ('google.ca', 'invalid url!'))



###############################################################################
class TestIsGenericUrl(unittest.TestCase):
    x = gluon.validators.IS_GENERIC_URL()
    
    
    def testInvalidUrls(self):
        urlsToCheckA = []
        for i in (range(0, 32) + [127]):
            #Control characters are disallowed in any part of a URL
            urlsToCheckA.append('http://www.benn' + chr(i) + '.ca')
        
        urlsToCheckB = [None, #the None type is not a URL
                        '', #the empty string is not a URL 
                        
                        #Disallowed characters as per RFC 2396, section 2.4.3
                       'http://www.no spaces allowed.com', # The ' ' character is illegal
                       'http://www.benn.ca/no spaces allowed/', # The ' ' character is illegal
                       'http://www.benn.ca/angle_<bracket/', # The '<' character is illegal
                       'http://www.benn.ca/angle_>bracket/', # The '>' character is illegal
                       'http://www.benn.ca/invalid%character', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/illegal%%20use', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/illegaluse%', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/illegaluse%0', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/illegaluse%x', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/ill%egaluse%x', # "%" must be followed by two hexadecimal digits
                       'http://www.benn.ca/double"quote/', # The '"' character is illegal
                       'http://www.curly{brace.com', # The '{' character is illegal
                       'http://www.benn.ca/curly}brace/', # The '}' character is illegal
                       'http://www.benn.ca/or|symbol/', # The '|' character is illegal
                       'http://www.benn.ca/back\slash', # The '\' character is illegal
                       'http://www.benn.ca/the^carat', # The '^' character is illegal
                       'http://left[bracket.me', # The '[' character is illegal
                       'http://www.benn.ca/right]bracket', # The ']' character is illegal
                       'http://www.benn.ca/angle`quote', # The '`' character is illegal
                       
                       #Additional characters that are invalid in schemes, as per RFC 2396, section 3.1
                       #Note, that we can't test '/' and '?' because they screw up the parsing, which
                       #lead to alternate *valid*, albeit unintended, interpretations
                       '-ttp://www.benn.ca', # May only begin a scheme with a letter
                       '+ttp://www.benn.ca', # May only begin a scheme with a letter
                       '.ttp://www.benn.ca', # May only begin a scheme with a letter
                       '9ttp://www.benn.ca', # May only begin a scheme with a letter
                       'ht;tp://www.benn.ca', # The ';' character is illegal in schemes
                       'ht@tp://www.benn.ca', # The '@' character is illegal in schemes
                       'ht&tp://www.benn.ca', # The '&' character is illegal in schemes
                       'ht=tp://www.benn.ca', # The '=' character is illegal in schemes
                       'ht$tp://www.benn.ca', # The '$' character is illegal in schemes
                       'ht,tp://www.benn.ca', # The ',' character is illegal in schemes
                       'ht:tp://www.benn.ca', # The ':' character is illegal in schemes
                       
                       #Invalid schemes
                       'htp://invalid_scheme.com', #the "htp" scheme does not exist
                       
                       #Note: remaining URI components (authority, path, query, fragment) cannot be specifically
                       #tested, because they are so generic that anything that doesn't contain illegal characters
                       #is valid in at least one of the possible interpretations
                       ]
        
        failures = []
        
        for url in (urlsToCheckA + urlsToCheckB):
            if self.x(url)[1] == None:
                failures.append('Incorrectly accepted: ' + str(url))
                
        if len(failures) > 0:
            self.fail(failures)
    
    
    def testValidUrls(self):
        urlsToCheck = [#Canonical examples from RFC 2396
                       'ftp://ftp.is.co.za/rfc/rfc1808.txt',
                       'gopher://spinaltap.micro.umn.edu/00/Weather/California/Los%20Angeles',
                       'http://www.math.uio.no/faq/compression-faq/part1.html',
                       'mailto:mduerst@ifi.unizh.ch',
                       'news:comp.infosystems.www.servers.unix',
                       'telnet://melvyl.ucop.edu/',
                       
                       'hTTp://www.benn.ca', # letters of the scheme should be interpreted as lowercase
                       '%66%74%70://ftp.is.co.za/rfc/rfc1808.txt', # unescape before checking scheme validity
                       '%46%74%70://ftp.is.co.za/rfc/rfc1808.txt', # escapes result in 'Ftp'
                       '/faq/compression-faq/part1.html', #relative URL
                       'google.com', #abbreviated URL
                       'www.google.com:8080', #abbreviated URL
                       '128.127.123.250:8080', #abbreviated URL
                       'blargg:ping', #the "blargg" scheme does not exist, but it's ambiguous whether this is an abbreviated URL or not
                       
                       #A few more random examples that should work
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
                       'file:///C:/Documents%20and%20Settings/Jonathan/Desktop/view.py']
        
        failures = []
        
        for url in urlsToCheck:
            if self.x(url)[1] != None:
                failures.append('Incorrectly rejected: ' + str(url))
                
        if len(failures) > 0:
            self.fail(failures)


    def testPrepending(self):
        self.assertEqual(self.x('google.ca'), ('google.ca', None)) #Does not prepend scheme for abbreviated domains
        self.assertEqual(self.x('google.ca:8080'), ('google.ca:8080', None)) #Does not prepend scheme for abbreviated domains
        self.assertEqual(self.x('https://google.ca'), ('https://google.ca', None)) #Does not prepend when scheme already exists
        
        #Does not prepend if None type is not specified in allowed_scheme, because a scheme is required 
        y = gluon.validators.IS_GENERIC_URL(allowed_schemes=['http', 'blargg'], prepend_scheme='http')
        self.assertEqual(y('google.ca'), ('google.ca', 'invalid url!'))
        
        

###############################################################################
class TestIsHttpUrl(unittest.TestCase):
    x = gluon.validators.IS_HTTP_URL()
    
    
    def testInvalidUrls(self):
        urlsToCheck = [None, #the None type is not an http URL
                       '', #the empty string is not an http URL 
                       'http://invalid' + chr(2) +'.com', #test that generic URL tests are being made
                       
                       'htp://invalid_scheme.com', #the "htp" scheme is not "http" or "https"
                       'blargg://invalid_scheme.com', #the "blargg" scheme is not "http" or "https"
                       
                       'http://-123.com', #hostnames may not have dashes at the start or end
                       'http://abcd-.ca', #hostnames may not have dashes at the start or end
                       'http://-abc123-.me', #hostnames may not have dashes at the start or end
                       'http://www.dom&ain.com/', #only alphanumeric characters and dash allowed
                       'http://www.dom=ain.com/', #only alphanumeric characters and dash allowed
                       'http://www.benn.ca&', #an illegal character at the end is still caught
                       'http://%62%65%6E%6E%2E%63%61/path', #no escaped characters allowed in host name
                       
                       'http://.domain.com', #leading dot before domain is not permitted
                       'http://.domain.com./path', #leading dot before domain is not permitted
                       'http://domain..com', #not allowed multiple dots at once
                       'http://domain...at..com', #not allowed multiple dots at once
                       'http://domain.com..', #not allowed multiple dots at once
                       'http://domain.com../path', #not allowed multiple dots at once
                       
                       'http://domain.3m', #toplabel must start with a letter
                       'http://domain.-3m', #toplabel cannot start or end with a dash
                       'http://domain.3m-', #toplabel cannot start or end with a dash
                       'http://domain.-3m-', #toplabel cannot start or end with a dash
                       'http://domain.co&m', #toplabel can only contain alphanumeric characters and dash
                       
                       'http://domain.m3456', #top-level domain 'm3456' does not exist
                       'http://domain.m-3/path#fragment', #top-level domain 'm-3' does not exist
                       'http://domain.m---k/path?query=value', #top-level domain 'm---k' does not exist
                       
                       'http://23.32..', #IPv4address must have 4 components
                       'http://23..32.56.0', #IPv4address can't have more than one '.' in a row
                       'http://38997.222.999', #IPv4address has 4 components
                       'http://23.32.56.99.', #IPv4address can't have an extra dot at the end
                       'http://.23.32.56.99', #IPv4address can't have an extra dot at the start
                       'http://.23.32.56.99.', #IPv4address can't have extra dots at both ends 
                       'http://w127.123.0.256:8080', #can't mix IPv4address with letters 
                       
                       'http://23.32.56.99:abcd', #port can't contain letters
                       'http://23.32.56.99:23cd', #port can't contain letters
                       'http://google.com:cd22', #port can't contain letters
                       'http://23.32:1300.56.99', #port can't be embedded in ip address
                       'http://www.yahoo:1600.com', #port can't be embedded in hostname
                       
                       'path/segment/without/starting/slash', #'path' will be interpreted as a domain, and fail
                       'http://www.math.uio.no;param=3', #path is missing slash, hence 'param' will be interpreted as part of domain and fail
                       '://ABC.com:/%7esmith/home.html' #invalid use of ':' at the start
                       ]
        
        failures = []
        
        for url in urlsToCheck:
            if self.x(url)[1] == None:
                failures.append('Incorrectly accepted: ' + str(url))
                
        if len(failures) > 0:
            self.fail(failures)
    
    
    def testValidUrls(self):
        
        urlsToCheck = [#Canonical examples from RFC 2616, Section 3.2.3
                       'http://abc.com:80/~smith/home.html',
                       'http://ABC.com/%7Esmith/home.html',
                       'http://ABC.com:/%7esmith/home.html',
                       
                       'http://www.math.uio.no/faq/compression-faq/part1.html', #from RFC 2396
                       
                       '//google.ca/faq/compression-faq/part1.html', #relative URL, no scheme
                       '//google.ca/faq;param=3', #relative URL, no scheme + param
                       '//google.ca/faq/index.html?query=5', #relative URL, no scheme + query
                       '//google.ca/faq/index.html;param=value?query=5', #relative URL, no scheme + param + query
                       '/faq/compression-faq/part1.html', #relative URL, no scheme or authority
                       '/faq;param=3', #relative URL, no scheme or authority + param
                       '/faq/index.html?query=5', #relative URL, no scheme or authority + query
                       '/faq/index.html;param=value?query=5', #relative URL, no scheme or authority + param + query
                       
                       'google.com', #abbreviated URL
                       'benn.ca/init/default', #abbreviated URL with path
                       'benn.ca/init;param=value/default?query=value', #abbreviated URL with parameter and query
                       
                       'http://host-name---with-dashes.me', # host name containing dashes
                       'http://www.host-name---with-dashes.me', # host name containing dashes
                       'http://a.com', # single character host names
                       'http://a.3.com', # single character host names
                       'http://a.bl-ck.com', # single character host names
                       'http://bl-e.b.com', # single character host names
                       'http://host123with456numbers.ca', #hostname containing numbers
                       'http://1234567890.com.', #hostname composed only of numbers
                       'http://1234567890.com./path', #hostname composed only of numbers, with path
                       
                       'http://google.com./path', #trailing dot after top-level domain is permitted
                       
                       'http://domain.xn--0zwm56d', #simplified Chinese test domain
                       
                       'http://127.123.0.256', #ip address instead of hostname
                       'http://127.123.0.256/document/drawer', #ip address instead of hostname
                       '127.123.0.256/document/', #ip address instead of hostname
                       '156.212.123.100', #ip address instead of hostname
                       
                       'http://www.google.com:180200', #port can be any length
                       'http://www.google.com:8080/path',
                       'http://www.google.com:8080',
                       '//www.google.com:8080',
                       'www.google.com:8080',
                       'http://127.123.0.256:8080/path',
                       '//127.123.0.256:8080',
                       '127.123.0.256:8080',
                       
                       'http://example.me??query=value?', #the query part can contain any valid characters, even another '?'
                       
                       #A few more random examples that should work
                       'http://a.com',
                       'http://3.com',
                       'http://www.benn.ca',
                       'http://benn.ca',
                       'http://amazon.com/books/',
                       'https://amazon.com/movies',
                       'hTTp://allcaps.com',
                       'http://localhost', #localhost is a top-level domain!
                       'HTTPS://localhost.', #as a top-level domain, localhost can have a trailing dot
                       'http://localhost#fragment',
                       'http://localhost/hello;param=value',
                       'http://localhost/hello;param=value/hi;param2=value2;param3=value3',
                       'http://localhost/hello?query=True',
                       'http://www.benn.ca/hello;param=value/hi;param2=value2;param3=value3/index.html?query=3',
                       'http://localhost/hello/?query=1500&five=6',
                       'http://localhost:8080',
                       'http://localhost:8080/',
                       'http://localhost:8080/hello',
                       'http://localhost:8080/hello%20world/',
                       'http://www.a.3.be-nn.5.ca', #this is an odd subdomain, but technically valid
                       'http://www.amazon.COM' #domains are case-insensitive
                       ]
        
        failures = []
        
        for url in urlsToCheck:
            if self.x(url)[1] != None:
                failures.append('Incorrectly rejected: ' + str(url))
                
        if len(failures) > 0:
            self.fail(failures)


    def testPrepending(self):
        self.assertEqual(self.x('google.ca'), ('http://google.ca', None)) #prepends scheme for abbreviated domains
        self.assertEqual(self.x('google.ca:8080'), ('http://google.ca:8080', None)) #prepends scheme for abbreviated domains
        self.assertEqual(self.x('https://google.ca'), ('https://google.ca', None)) #does not prepend when scheme already exists
        
        y = gluon.validators.IS_HTTP_URL(prepend_scheme='https')
        self.assertEqual(y('google.ca'), ('https://google.ca', None)) #prepends https if asked
        
        z = gluon.validators.IS_HTTP_URL(prepend_scheme=None)
        self.assertEqual(z('google.ca:8080'), ('google.ca:8080', None)) #prepending disabled
        
        try:
            gluon.validators.IS_HTTP_URL(prepend_scheme='mailto')
        except Exception, e:
            if str(e) != "prepend_scheme='mailto' is not in allowed_schemes=[None, 'http', 'https']":
                self.fail("Wrong exception: " + str(e))
        else:
            self.fail("Got invalid prepend_scheme: 'mailto'")
        
        #Does not prepend if None type is not specified in allowed_scheme, because a scheme is required 
        a = gluon.validators.IS_HTTP_URL(allowed_schemes=['http'])
        self.assertEqual(a('google.ca'), ('google.ca', 'invalid url!'))
        self.assertEqual(a('google.ca:80'), ('google.ca:80', 'invalid url!'))
        

###############################################################################
if __name__ == "__main__":
    unittest.main()
    
