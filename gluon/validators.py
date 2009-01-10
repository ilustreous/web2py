"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
Thanks to ga2arch for help with IS_IN_DB and IS_NOT_IN_DB on GAE
License: GPL v2
"""

import os, re, copy, sys, types, datetime, time, cgi, hmac
try: 
    import hashlib
    have_hashlib = True
except:
    import sha, md5
    have_hashlib = False
from storage import Storage

__all__ = ['IS_ALPHANUMERIC', 'IS_DATE', 'IS_DATETIME', 'IS_EMAIL', 'IS_EXPR', 'IS_FLOAT_IN_RANGE', 'IS_INT_IN_RANGE', 'IS_IN_SET', 'IS_LENGTH', 'IS_LIST_OF', 'IS_LOWER', 'IS_MATCH', 'IS_NOT_EMPTY', 'IS_TIME', 'IS_URL', 'CLEANUP', 'CRYPT', 'IS_IN_DB', 'IS_NOT_IN_DB', 'IS_UPPER', 'IS_NULL_OR']

class IS_MATCH(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_MATCH('.+'))
    
    the argument of IS_MATCH is a regular expression.

    IS_MATCH('.+')('hello') returns ('hello',None)
    IS_MATCH('.+')('') returns ('','invalid!')   
    """
    def __init__(self, expression, error_message='invalid expression!'):
        self.regex = re.compile(expression)
        self.error_message = error_message
    def __call__(self, value):
        match = self.regex.match(value)        
        if match: return (match.group(), None)
        return (value, self.error_message)

class IS_EXPR(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_EXPR('5<int(value)<10'))
    
    the argument of IS_EXPR must be python condition

    IS_EXPR('int(value)<2')('1') returns (1,None)
    IS_EXPR('int(value)<2')('2') returns ('2','invalid expression!')   
    """
    def __init__(self, expression, error_message='invalid expression!'):
        self.expression = expression
        self.error_message = error_message
    def __call__(self, value):        
        environment = {'value':value}
        exec('__ret__=' + self.expression) in environment
        if environment['__ret__']: return (value, None)        
        return (value, self.error_message)

class IS_LENGTH(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_LENGTH(32))
    
    the argument of IS_LENGTH is the man number of characters
    """
    def __init__(self, size, error_message='too long!'):
        self.size = size
        self.error_message = error_message
    def __call__(self, value):
        if isinstance(value, cgi.FieldStorage):
            if value.file:
                value.file.seek(0, os.SEEK_END)
                length = value.file.tell()
                value.file.seek(0, os.SEEK_SET)
            else:
                val = value.value
                if val: length = len(val)
                else: length = 0
            if length <= self.size: return (value, None) # for uploads
        elif isinstance(value, (str, unicode, list)): 
            if len(value) <= self.size: return (value, None)      
        elif len(str(value))<=self.size:
            try: value.decode('utf8')
            except: return (value,'Not Unicode')
            return (value,None)
        return (value, self.error_message)

class IS_IN_SET(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_SET(['max','john']))
    
    the argument of IS_IN_SET must be a list or set
    """
    def __init__(self, theset, labels=None, error_message='value not allowed!',multiple=False):
        self.multiple=multiple
        self.theset = [str(item) for item in theset]
        if isinstance(theset,dict): self.labels=theset.values()
        else: self.labels=labels
        self.error_message = error_message
    def options(self):
        if not self.labels:
            return [(k, k) for i, k in enumerate(self.theset)]
        return [(k, self.labels[i]) for i, k in enumerate(self.theset)]
    def __call__(self, value):
        if self.multiple: values=re.compile("[\w\-:]+").findall(str(value))
        else: values=[value]
        failures=[x for x in values if not x in self.theset]
        if failures: return (value, self.error_message)
        if self.multiple: return ('|%s|'%'|'.join(values),None)
        return (value, None)

regex1 = re.compile('[\w_]+\.[\w_]+')
regex2 = re.compile('%\((?P<name>[^\)]+)\)s')

class IS_IN_DB(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_DB(db,db.table))

    used for reference fields, rendered as a dropbox
    """
    def __init__(self,dbset,field,label=None,error_message='value not in database!',orderby=None,cache=None,multiple=False):
        if hasattr(dbset,'define_table'): self.dbset=dbset()
        else: self.dbset=dbset        
        self.field=field
        ktable,kfield=str(self.field).split('.')
        if not label:
            label='%%(%s)s' % kfield
        elif regex1.match(str(label)):
            label='%%(%s)s' % str(label).split('.')[-1]
        ks=regex2.findall(label)
        if not kfield in ks: ks+=[kfield]
        fields=['%s.%s'%(ktable,k) for k in ks]
        self.fields=fields
        self.label=label
        self.ktable=ktable
        self.kfield=kfield
        self.ks=ks
        self.error_message=error_message
        self.theset=None
        self.orderby=orderby
        self.cache=cache
        self.multiple=multiple
    def build_set(self):
        if self.dbset._db._dbname!='gql':
           orderby=self.orderby or ', '.join(self.fields)
           dd=dict(orderby=orderby,cache=self.cache)
           records=self.dbset.select(*self.fields,**dd)
        else:
           import contrib.gql
           orderby=self.orderby or \
             contrib.gql.SQLXorable('|'.join([k for k in self.ks if k!='id']))
           dd=dict(orderby=orderby,cache=self.cache)
           records=self.dbset.select(self.dbset._db[self.ktable].ALL,**dd)
        self.theset=[str(r[self.kfield]) for r in records]
        self.labels=[self.label % dict(r) for r in records]        
    def options(self):
        self.build_set()
        return [(k,self.labels[i]) for i,k in enumerate(self.theset)]
    def __call__(self,value):
        if self.multiple:
            values=re.compile("[\w\-:]+").findall(str(value))
            if not [x for x in values if not x in self.theset]:
                return ('|%s|'%'|'.join(values),None)
        elif self.theset:
            if value in self.theset:
                return (value,None)
        else:
            ktable,kfield=str(self.field).split('.')
            field=self.dbset._db[ktable][kfield]
            if self.dbset(field==value).count(): return (value,None)
        return (value,self.error_message)         

class IS_NOT_IN_DB(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_IN_DB(db,db.table))
 
    makes the field unique
    """
    def __init__(self,dbset,field,error_message='value already in database!'):
        if hasattr(dbset,'define_table'): self.dbset=dbset()
        else: self.dbset=dbset
        self.field=field
        self.error_message=error_message
        self.record_id=0
    def set_self_id(self,id): self.record_id=id
    def __call__(self,value):
        tablename,fieldname=str(self.field).split('.')
        field=self.dbset._db[tablename][fieldname]
        rows=self.dbset(field==value).select(limitby=(0,1))
        if len(rows)>0 and str(rows[0].id)!=str(self.record_id): 
            return (value,self.error_message)
        return (value,None)

class IS_INT_IN_RANGE(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_INT_IN_RANGE(0,10))
    """
    def __init__(self, minimum, maximum, error_message='too small or too large!'):
        self.minimum=int(minimum)
        self.maximum=int(maximum)
        self.error_message = error_message
    def __call__(self, value):
        try:
            fvalue = float(value)
            value = int(value)
            if value == fvalue and self.minimum <= value < self.maximum: 
                return (value, None)
        except ValueError: pass
        return (value, self.error_message)

class IS_FLOAT_IN_RANGE(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_FLOAT_IN_RANGE(0,10))
    """
    def __init__(self, minimum, maximum, error_message='too small or too large!'):
        self.minimum=float(minimum)
        self.maximum=float(maximum)
        self.error_message = error_message
    def __call__(self, value):        
        try:
            value = float(value)
            if self.minimum <= value <= self.maximum: return (value, None)
        except ValueError: pass
        return (value, self.error_message)

class IS_NOT_EMPTY(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_EMPTY())
    """
    def __init__(self, error_message='cannot be empty!'):
        self.error_message = error_message
    def __call__(self, value):
        if value == None or value == '' or value == []: 
            return (value, self.error_message)
        return (value, None)

class IS_ALPHANUMERIC(IS_MATCH): 
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_ALPHANUMERIC())
    """
    def __init__(self, error_message='must be alphanumeric!'):
        IS_MATCH.__init__(self, '^[\w]*$', error_message)

class IS_EMAIL(IS_MATCH):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_EMAIL())
    """
    def __init__(self, error_message='invalid email!'):
        IS_MATCH.__init__(self, '^\w+(.\w+)*@(\w+.)+(\w+)$', error_message)

#URL scheme source:  <http://en.wikipedia.org/wiki/URI_scheme> obtained on 2008-Nov-10
official_url_schemes = ['aaa', 'aaas', 'acap', 'cap', 'cid', 'crid', 'data', 'dav', 'dict', 'dns', 'fax', 'file',
                        'ftp', 'go', 'gopher', 'h323', 'http', 'https', 'icap', 'im', 'imap', 'info', 'ipp',
                        'iris', 'iris.beep', 'iris.xpc', 'iris.xpcs', 'iris.lws', 'ldap', 'mailto', 'mid', 'modem',
                        'msrp', 'msrps', 'mtqp', 'mupdate', 'news', 'nfs', 'nntp', 'opaquelocktoken', 'pop',
                        'pres', 'prospero', 'rtsp', 'service', 'shttp', 'sip', 'sips', 'snmp', 'soap.beep',
                        'soap.beeps', 'tag', 'tel', 'telnet', 'tftp', 'thismessage', 'tip', 'tv', 'urn', 'vemmi',
                        'wais', 'xmlrpc.beep', 'xmlrpc.beep', 'xmpp', 'z39.50r', 'z39.50s']
unofficial_url_schemes = ['about', 'adiumxtra', 'aim', 'afp', 'aw', 'callto', 'chrome', 'cvs', 'ed2k', 'feed',
                          'fish', 'gg', 'gizmoproject', 'iax2', 'irc', 'ircs', 'itms', 'jar', 'javascript',
                          'keyparc', 'lastfm', 'ldaps', 'magnet', 'mms', 'msnim', 'mvn', 'notes', 'nsfw', 'psyc',
                          'paparazzi:http', 'rmi', 'rsync', 'secondlife', 'sgn', 'skype', 'ssh', 'sftp', 'smb',
                          'sms', 'soldat', 'steam', 'svn', 'teamspeak', 'unreal', 'ut2004', 'ventrilo',
                          'view-source', 'webcal', 'wyciwyg', 'xfire', 'xri', 'ymsgr']
all_url_schemes = [None] + official_url_schemes + unofficial_url_schemes
http_schemes = [None, 'http', 'https']

def unescape_url(url):
    '''
    Unescapes characters in a URL string. e.g. "%20" will become " " 
    
    @param url a string containing the url, or a part of the url, whose characters we wish to unescape
    @return the inputed string, but with any escaped characters made unescaped
    '''
    s = str(url)
    index = 0
    while (True):
        index = s.find('%', index)
        if index == - 1:
            break
        s = s.replace(s[index:index + 3], chr(eval('0x' + s[index + 1:index + 3])))
        
    return s
    
#This regex comes from RFC 2396, Appendix B. It's used to split a URL into its component parts
#Here are the regex groups that it extracts:
#    scheme = group(2)
#    authority = group(4)
#    path = group(5)
#    query = group(7)
#    fragment = group(9)
url_split_regex = re.compile('^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?')

class IS_GENERIC_URL(object):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The URL scheme specified (if one is specified) is not valid

    Based on RFC 2396: http://www.faqs.org/rfcs/rfc2396.html
    
    This function only checks the URL's syntax. It does not check that the URL points to a real document, 
    for example, or that it otherwise makes sense semantically. This function does automatically prepend
    'http://' in front of a URL if and only if that's necessary to successfully parse the URL. Please note 
    that a scheme will be prepended only for rare cases (e.g. 'google.ca:80')
    
    The list of allowed schemes is customizable with the allowed_schemes parameter. If you exclude None from
    the list, then abbreviated URLs (lacking a scheme such as 'http') will be rejected.
    
    The default prepended scheme is customizable with the prepend_scheme parameter. If you set prepend_scheme
    to None then prepending will be disabled. URLs that require prepending to parse will still be accepted, 
    but the return value will not be modified.
    """
    def __init__(self, error_message='invalid url!', allowed_schemes=None, prepend_scheme=None):
        '''
        @param error_message a string, the error message to give the end user if the URL does not validate
        @param allowed_schemes a list containing strings or None. Each element is a scheme the inputed URL is allowed to use   
        @param prepend_scheme a string, this scheme is prepended if it's necessary to make the URL valid
        '''
        self.error_message = error_message
        if allowed_schemes == None:
            self.allowed_schemes = all_url_schemes
        else:
            self.allowed_schemes = allowed_schemes
        self.prepend_scheme = prepend_scheme
        if (self.prepend_scheme not in self.allowed_schemes) and (None in self.allowed_schemes):
            raise Exception("prepend_scheme='" + str(self.prepend_scheme) + "' is not in allowed_schemes=" + str(self.allowed_schemes))
            
    def __call__(self, value):
        '''
        @param value a string, the URL to validate
        @return a tuple, where tuple[0] is the inputed value (possible prepended with prepend_scheme),
                and tuple[1] is either None (success!) or the string error_message  
        '''
        try:
            #if the URL does not mis-use the '%' character
            if not re.compile(r"%[^0-9A-Fa-f]{2}|%[^0-9A-Fa-f][0-9A-Fa-f]|%[0-9A-Fa-f][^0-9A-Fa-f]|%$|%[0-9A-Fa-f]$|%[^0-9A-Fa-f]$").search(value):
                #if the URL is only composed of valid characters
                if re.compile(r"[A-Za-z0-9;/?:@&=+$,\-_\.!~*'\(\)%#]+$").match(value):
                    #Then split up the URL into its components and check on the scheme
                    scheme = url_split_regex.match(value).group(2) 

                    #Clean up the scheme before we check it
                    if scheme != None:
                        scheme = unescape_url(scheme).lower()
                    
                    #If the scheme really exists
                    if scheme in self.allowed_schemes:
                        #Then the URL is valid
                        return (value, None)
                    else:
                        #else, for the possible case of abbreviated URLs with ports, check to see if adding a valid 
                        #scheme fixes the problem (but only do this if it doesn't have one already!)
                        if not re.compile('://').search(value) and None in self.allowed_schemes:
                            schemeToUse = self.prepend_scheme or 'http'
                            prependTest = self.__call__(schemeToUse + '://' + value)
                            #if the prepend test succeeded
                            if prependTest[1] == None:
                                #if prepending in the output is enabled
                                if self.prepend_scheme:
                                    return prependTest
                                else:
                                    #else return the original, non-prepended value
                                    return (value, None)
        except:
            pass
        
        #else the URL is not valid
        return (value, self.error_message)


#Sources (obtained 2008-Nov-11): 
#    http://en.wikipedia.org/wiki/Top-level_domain
#    http://www.iana.org/domains/root/db/
official_top_level_domains = ['ac', 'ad', 'ae', 'aero', 'af', 'ag', 'ai', 'al', 'am', 'an', 'ao', 'aq', 'ar',
                              'arpa', 'as', 'asia', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 
                              'bg', 'bh', 'bi', 'biz', 'bj', 'bl', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bv', 
                              'bw', 'by', 'bz', 'ca', 'cat', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 
                              'cm', 'cn', 'co', 'com', 'coop', 'cr', 'cu', 'cv', 'cx', 'cy', 'cz', 'de', 'dj', 
                              'dk', 'dm', 'do', 'dz', 'ec', 'edu', 'ee', 'eg', 'eh', 'er', 'es', 'et', 'eu', 
                              'example', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga', 'gb', 'gd', 'ge', 'gf', 'gg', 
                              'gh', 'gi', 'gl', 'gm', 'gn', 'gov', 'gp', 'gq', 'gr', 'gs', 'gt', 'gu', 'gw', 
                              'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'im', 'in', 'info', 
                              'int', 'invalid', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jobs', 'jp', 
                              'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb', 'lc', 
                              'li', 'lk', 'localhost', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md', 
                              'me', 'mf', 'mg', 'mh', 'mil', 'mk', 'ml', 'mm', 'mn', 'mo', 'mobi', 'mp', 'mq', 
                              'mr', 'ms', 'mt', 'mu', 'museum', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'name', 'nc', 
                              'ne', 'net', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om', 'org', 
                              'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'pro', 'ps', 'pt', 
                              'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 
                              'sh', 'si', 'sj', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'st', 'su', 'sv', 'sy', 'sz', 
                              'tc', 'td', 'tel', 'test', 'tf', 'tg', 'th', 'tj', 'tk', 'tl', 'tm', 'tn', 'to', 
                              'tp', 'tr', 'travel', 'tt', 'tv', 'tw', 'tz', 'ua', 'ug', 'uk', 'um', 'us', 'uy', 
                              'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf', 'ws', 'xn--0zwm56d', 
                              'xn--11b5bs3a9aj6g', 'xn--80akhbyknj4f', 'xn--9t4b11yi5a', 'xn--deba0ad', 
                              'xn--g6w251d', 'xn--hgbk6aj7f53bba', 'xn--hlcj6aya9esc7a', 'xn--jxalpdlp', 
                              'xn--kgbechtv', 'xn--zckzah', 'ye', 'yt', 'yu', 'za', 'zm', 'zw']

class IS_HTTP_URL(object):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The string breaks any of the HTTP syntactic rules
       * The URL scheme specified (if one is specified) is not 'http' or 'https'
       * The top-level domain (if a host name is specified) does not exist

    Based on RFC 2616: http://www.faqs.org/rfcs/rfc2616.html
    
    This function only checks the URL's syntax. It does not check that the URL points to a real document, 
    for example, or that it otherwise makes sense semantically. This function does automatically prepend
    'http://' in front of a URL in the case of an abbreviated URL (e.g. 'google.ca').
    
    The list of allowed schemes is customizable with the allowed_schemes parameter. If you exclude None from
    the list, then abbreviated URLs (lacking a scheme such as 'http') will be rejected.
    
    The default prepended scheme is customizable with the prepend_scheme parameter. If you set prepend_scheme
    to None then prepending will be disabled. URLs that require prepending to parse will still be accepted, 
    but the return value will not be modified.
    """
    def __init__(self, error_message='invalid url!', allowed_schemes=None, prepend_scheme='http'):
        '''
        @param error_message a string, the error message to give the end user if the URL does not validate
        @param allowed_schemes a list containing strings or None. Each element is a scheme the inputed URL is allowed to use   
        @param prepend_scheme a string, this scheme is prepended if it's necessary to make the URL valid
        '''
        self.error_message = error_message
        if allowed_schemes == None:
            self.allowed_schemes = http_schemes
        else:
            self.allowed_schemes = allowed_schemes
        self.prepend_scheme = prepend_scheme
        
        for i in self.allowed_schemes:
            if i not in http_schemes:
                raise Exception("allowed_scheme value '" + str(i) + "' is not in " + str(http_schemes))
        if (self.prepend_scheme not in self.allowed_schemes) and (None in self.allowed_schemes):
            raise Exception("prepend_scheme='" + str(self.prepend_scheme) + "' is not in allowed_schemes=" + str(self.allowed_schemes))
            
        
    def __call__(self, value):
        '''
        @param value a string, the URL to validate
        @return a tuple, where tuple[0] is the inputed value (possible prepended with prepend_scheme),
                and tuple[1] is either None (success!) or the string error_message  
        '''
        try:
            #if the URL passes generic validation
            x = IS_GENERIC_URL(allowed_schemes=self.allowed_schemes, prepend_scheme=self.prepend_scheme)
            if x(value)[1] == None:
                componentsMatch = url_split_regex.match(value)
                authority = componentsMatch.group(4)
                
                #if there is an authority component
                if authority:
                    #if authority is a valid IP address
                    if re.compile('\d+\.\d+\.\d+\.\d+(:\d*)*$').match(authority):
                        #Then this HTTP URL is valid
                        return (value, None)
                    else:
                        #else if authority is a valid domain name
                        domainMatch = re.compile('(([A-Za-z0-9]+[A-Za-z0-9\-]*[A-Za-z0-9]+\.)*([A-Za-z0-9]+\.)*)*([A-Za-z]+[A-Za-z0-9\-]*[A-Za-z0-9]+)\.?(:\d*)*$').match(authority)
                        if domainMatch:
                            #if the top-level domain really exists
                            if domainMatch.group(4).lower() in official_top_level_domains:
                                #Then this HTTP URL is valid
                                return (value, None)
                else:
                    #else this is a relative/abbreviated URL, which will parse into the URL's path component
                    path = componentsMatch.group(5)
                    
                    #relative case: if this is a valid path (if it starts with a slash)
                    if re.compile('/').match(path):
                        #Then this HTTP URL is valid 
                        return (value, None)
                    else:
                        #abbreviated case: if we haven't already, prepend a scheme and see if it fixes the problem
                        if not re.compile('://').search(value):
                            schemeToUse = self.prepend_scheme or 'http'
                            prependTest = self.__call__(schemeToUse + '://' + value)
                            #if the prepend test succeeded
                            if prependTest[1] == None:
                                #if prepending in the output is enabled
                                if self.prepend_scheme:
                                    return prependTest
                                else:
                                    #else return the original, non-prepended value
                                    return (value, None)
        except:
            pass
        
        #else the HTTP URL is not valid
        return (value, self.error_message)


class IS_URL(object):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The string breaks any of the HTTP syntactic rules
       * The URL scheme specified (if one is specified) is not 'http' or 'https'
       * The top-level domain (if a host name is specified) does not exist

    Based on RFC 2616: http://www.faqs.org/rfcs/rfc2616.html
    
    This function only checks the URL's syntax. It does not check that the URL points to a real document, 
    for example, or that it otherwise makes sense semantically. This function does automatically prepend
    'http://' in front of a URL in the case of an abbreviated URL (e.g. 'google.ca').

    If the parameter mode='generic' is used, then this function's behaviour changes. It then rejects a URL 
    string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The URL scheme specified (if one is specified) is not valid

    Based on RFC 2396: http://www.faqs.org/rfcs/rfc2396.html
    
    The list of allowed schemes is customizable with the allowed_schemes parameter. If you exclude None from
    the list, then abbreviated URLs (lacking a scheme such as 'http') will be rejected.
    
    The default prepended scheme is customizable with the prepend_scheme parameter. If you set prepend_scheme
    to None then prepending will be disabled. URLs that require prepending to parse will still be accepted, 
    but the return value will not be modified.
    
    Examples:

    INPUT(_type='text',_name='name',requires=IS_URL())
    INPUT(_type='text',_name='name',requires=IS_URL(mode='generic'))
    INPUT(_type='text',_name='name',requires=IS_URL(allowed_schemes=['https']))
    INPUT(_type='text',_name='name',requires=IS_URL(prepend_scheme='https'))
    INPUT(_type='text',_name='name',requires=IS_URL(mode='generic', allowed_schemes=['ftps', 'https'], prepend_scheme='https'))
    """
    def __init__(self, error_message='invalid url!', mode='http', allowed_schemes=None, prepend_scheme='http'):
        '''
        @param error_message a string, the error message to give the end user if the URL does not validate
        @param allowed_schemes a list containing strings or None. Each element is a scheme the inputed URL is allowed to use   
        @param prepend_scheme a string, this scheme is prepended if it's necessary to make the URL valid
        '''
        self.error_message = error_message
        self.mode = mode #let the __call__ determine if it's correct
        self.allowed_schemes = allowed_schemes # let the sub-methods determine the correct default value

        if self.allowed_schemes:
            if (prepend_scheme not in self.allowed_schemes) and (None in self.allowed_schemes):
                raise Exception("prepend_scheme='" + str(prepend_scheme) + "' is not in allowed_schemes=" + str(self.allowed_schemes))
        #if allowed_schemes is None, then we will defer testing prepend_scheme's validity to a sub-method
        self.prepend_scheme = prepend_scheme
        
    def __call__(self, value):
        '''
        @param value a string, the URL to validate
        @return a tuple, where tuple[0] is the inputed value (possible prepended with prepend_scheme),
                and tuple[1] is either None (success!) or the string error_message  
        '''
        try:
            subMethod = eval("IS_" + str(self.mode).upper() + "_URL(allowed_schemes=self.allowed_schemes, prepend_scheme=self.prepend_scheme)")
        except Exception, e:
            if re.compile("name 'IS_.*_URL' is not defined$").match(str(e)):
                raise Exception("mode='" + str(self.mode) + "' is not valid")
            else:
                raise e
        return subMethod(value)


regex_time = re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?((?P<d>[ap]m))?')

class IS_TIME(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_TIME())

    understands the follwing formats
    hh:mm:ss [am/pm]
    hh:mm [am/pm]
    hh [am/pm]

    [am/pm] is options, ':' can be replaced by any other non-digit
    """
    def __init__(self, error_message='must be HH:MM:SS!'):
        self.error_message = error_message
    def __call__(self, value):
        try:
            ivalue = value
            value = regex_time.match(value.lower())
            h, m, s = int(value.group('h')), 0, 0
            if value.group('m') != None: m = int(value.group('m'))
            if value.group('s') != None: s = int(value.group('s'))
            if value.group('d') == 'pm' and 0 < h < 12: h = h + 12
            if not (h in range(24) and m in range(60) and s in range(60)):
                raise ValueError
            value = datetime.time(h,m,s)
            return (value, None)
        except AttributeError: pass
        except ValueError: pass
        return (ivalue, self.error_message)

class IS_DATE(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_DATE())

    date has to be in the ISO8960 format YYYY-MM-DD
    """
    def __init__(self, format='%Y-%m-%d', error_message='must be YYYY-MM-DD!'):
        self.format = format
        self.error_message = error_message
    def __call__(self, value):
        try:
            y, m, d, hh, mm, ss, t0, t1, t2 = time.strptime(value, str(self.format))
            value = datetime.date(y, m, d)
            return (value, None)
        except:
            return (value, self.error_message)
    def formatter(self, value):
        return value.strftime(str(self.format))

class IS_DATETIME(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_DATETIME())

    datetime has to be in the ISO8960 format YYYY-MM-DD hh:mm:ss
    """
    isodatetime = '%Y-%m-%d %H:%M:%S'
    def __init__(self, format='%Y-%m-%d %H:%M:%S', error_message='must be YYYY-MM-DD HH:MM:SS!'):
        self.format = format
        self.error_message = error_message        
    def __call__(self, value):
        try:
            y, m, d, hh, mm, ss, t0, t1, t2 = time.strptime(value, str(self.format))
            value = datetime.datetime(y, m, d, hh, mm, ss)
            return (value, None)
        except:
            return (value, self.error_message)
    def formatter(self, value):
        return value.strftime(str(self.format))

class IS_LIST_OF(object):
    def __init__(self, other):
        self.other = other
    def __call__(self, value):
        ivalue = value
        if not isinstance(value, list): ivalue = [ivalue]
        new_value = []
        for item in ivalue:
            v, e = self.other(item)
            if e: return (value, e)
            else: new_value.append(v)
        return (new_value, None)

class IS_LOWER(object):
    def __call__(self, value): return (value.lower(), None)

class IS_UPPER(object):
    def __call__(self, value): return (value.upper(), None)

class IS_NULL_OR(object):
    def __init__(self, other, null=None):
        self.other, self.null, self.multiple = other, null, False
    def set_self_id(self, id):
        if hasattr(self.other, 'set_self_id'):
            self.other.set_self_id(id)
    def __call__(self, value):
        if not value: return (self.null, None)
        return self.other(value)
    def formatter(self, value):
        if hasattr(self.other, 'formatter'):
            return self.other.formatter(value)
        return value

class CLEANUP(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=CLEANUP())

    removes special characters on validation
    """   
    def __init__(self): pass
    def __call__(self, value):
        v = ''
        for c in str(value).strip():
            if ord(c) in [10, 13] + range(32, 127): v += c
        return (v, None)

class CRYPT(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=CRYPT())

    encodes the value on validation with md5 checkshum
    """   
    def __init__(self, key=None):
        self.key = key
    def __call__(self, value):        
        if self.key: 
            if have_hashlib: return (hmac.new(self.key, value, hashlib.sha512).hexdigest(), None)
            else: return (hmac.new(self.key, value, sha).hexdigest(), None)
        if have_hashlib: return (hashlib.md5(value).hexdigest(), None)
        else: return (md5.new(value).hexdigest(), None)

class IS_IN_SUBSET(IS_IN_SET):
    def __init__(self,*a,**b):
        IS_IN_SET.__init__(self,*a,**b)
    def __call__(self,value):
        values=re.compile("\w+").findall(str(value))
        failures=[x for x in values if IS_IN_SET.__call__(self,x)[1]]
        if failures: return (value,self.error_message)
        return (value,None)
