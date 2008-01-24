"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import re

# pattern to find defined tables 
regex_tables=re.compile("""^[\w]+\.define_table\(\s*[\'\"](?P<name>[\w_]+)[\'\"]""",flags=re.M)

# pattern to find exposed functions in controller
regex_expose=re.compile('^def[ ]+(?P<name>[\w_]+)\(\)',flags=re.M)

regex_include=re.compile('(?P<all>\{\{\s*include\s+[\'"](?P<name>[^\']*)[\'"]\s*\}\})')

regex_extend=re.compile('^\s*(?P<all>\{\{\s*extend\s+[\'"](?P<name>[^\']+)[\'"]\s*\}\})')
