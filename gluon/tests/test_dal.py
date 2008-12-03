'''
    Unit tests for gluon.cache
'''

import unittest, os, datetime
from gluon.sql import *

class TestFields(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        for ft in ['string','text','password','upload','blob']:
            self.assertEqual(db.define_table('t',db.Field('a',ft,default=''))._db,db)
            self.assertEqual(db.t.drop(),None)        
        self.assertEqual(db.define_table('t',db.Field('a','integer',default=1))._db,db)
        self.assertEqual(db.t.drop(),None)
        self.assertEqual(db.define_table('t',db.Field('a','double',default=1))._db,db)
        self.assertEqual(db.t.drop(),None)
        self.assertEqual(db.define_table('t',db.Field('a','boolean',default=True))._db,db)
        self.assertEqual(db.t.drop(),None)
        self.assertEqual(db.define_table('t',db.Field('a','date',default=datetime.date.today()))._db,db)
        self.assertEqual(db.t.drop(),None)
        self.assertEqual(db.define_table('t',db.Field('a','datetime',default=datetime.datetime.today()))._db,db)
        self.assertEqual(db.t.drop(),None)
        self.assertEqual(db.define_table('t',db.Field('a','time',default='11:30'))._db,db)
        self.assertEqual(db.t.drop(),None)

class TestInsert(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a'))._db,db)
        self.assertEqual(db.t.insert(a='1'),1)
        self.assertEqual(db.t.insert(a='1'),2)
        self.assertEqual(db.t.insert(a='1'),3)
        self.assertEqual(db(db.t.a=='1').count(),3)
        self.assertEqual(db(db.t.a=='1').update(a='2'),None)
        self.assertEqual(db(db.t.a=='2').count(),3)
        self.assertEqual(db(db.t.a=='2').delete(),None)
        self.assertEqual(db.t.drop(),None)

class TestSelect(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a'))._db,db)
        self.assertEqual(db.t.insert(a='1'),1)
        self.assertEqual(db.t.insert(a='2'),2)
        self.assertEqual(db.t.insert(a='3'),3)
        self.assertEqual(len(db(db.t.id>0).select()),3)
        self.assertEqual(len(db().select(db.t.ALL)),3)
        self.assertEqual(len(db(db.t.a==None).select()),0)
        self.assertEqual(len(db(db.t.a!=None).select()),3)
        self.assertEqual(len(db(db.t.a>'1').select()),2)
        self.assertEqual(len(db(db.t.a>='1').select()),3)
        self.assertEqual(len(db(db.t.a=='1').select()),1)
        self.assertEqual(len(db(db.t.a!='1').select()),2)
        self.assertEqual(len(db(db.t.a<'3').select()),2)
        self.assertEqual(len(db(db.t.a<='3').select()),3)
        self.assertEqual(len(db(db.t.a>'1')(db.t.a<'3').select()),1)
        self.assertEqual(len(db((db.t.a>'1')&(db.t.a<'3')).select()),1)
        self.assertEqual(len(db((db.t.a>'1')|(db.t.a<'3')).select()),3)
        self.assertEqual(len(db((db.t.a>'1')&~(db.t.a>'2')).select()),1)
        self.assertEqual(len(db(~(db.t.a>'1')&(db.t.a>'2')).select()),0)
        self.assertEqual(db.t.drop(),None)

class TestBelongs(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a'))._db,db)
        self.assertEqual(db.t.insert(a='1'),1)
        self.assertEqual(db.t.insert(a='2'),2)
        self.assertEqual(db.t.insert(a='3'),3)
        self.assertEqual(len(db(db.t.a.belongs(('1','3'))).select()),2)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.id>2)._select(db.t.a))).select()),1)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.a.belongs(('1','3')))._select(db.t.a))).select()),2)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.a.belongs(db(db.t.a.belongs(('1','3')))._select(db.t.a)))._select(db.t.a))).select()),2)
        self.assertEqual(db.t.drop(),None)

class TestLike(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a'))._db,db)
        self.assertEqual(db.t.insert(a='abc'),1)
        self.assertEqual(len(db(db.t.a.like('a%')).select()),1)
        self.assertEqual(len(db(db.t.a.like('%b%')).select()),1)
        self.assertEqual(len(db(db.t.a.like('%c')).select()),1)
        self.assertEqual(len(db(db.t.a.like('%d%')).select()),0)
        self.assertEqual(len(db(db.t.a.lower().like('A%')).select()),1)
        self.assertEqual(len(db(db.t.a.lower().like('%B%')).select()),1)
        self.assertEqual(len(db(db.t.a.lower().like('%C')).select()),1)
        self.assertEqual(len(db(db.t.a.upper().like('A%')).select()),1)
        self.assertEqual(len(db(db.t.a.upper().like('%B%')).select()),1)
        self.assertEqual(len(db(db.t.a.upper().like('%C')).select()),1)
        self.assertEqual(db.t.drop(),None)

class TestDatetime(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a','datetime'))._db,db)
        self.assertEqual(db.t.insert(a=datetime.datetime(1971,12,21,11,30)),1)
        self.assertEqual(db.t.insert(a=datetime.datetime(1971,11,21,10,30)),2)
        self.assertEqual(db.t.insert(a=datetime.datetime(1970,12,21,9,30)),3)
        self.assertEqual(len(db(db.t.a==datetime.datetime(1971,12,21,11,30)).select()),1)
        self.assertEqual(len(db(db.t.a.year()==1971).select()),2)
        self.assertEqual(len(db(db.t.a.month()==12).select()),2)
        self.assertEqual(len(db(db.t.a.day()==21).select()),3)
        self.assertEqual(len(db(db.t.a.hour()==11).select()),1)
        self.assertEqual(len(db(db.t.a.minutes()==30).select()),3)
        self.assertEqual(len(db(db.t.a.seconds()==0).select()),3)
        self.assertEqual(db.t.drop(),None)

class TestExpressions(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t',db.Field('a','integer'))._db,db)
        self.assertEqual(db.t.insert(a=1),1)
        self.assertEqual(db.t.insert(a=2),2)
        self.assertEqual(db.t.insert(a=3),3)        
        self.assertEqual(db(db.t.a==3).update(a=db.t.a+1),None)        
        self.assertEqual(len(db(db.t.a==4).select()),1)        
        self.assertEqual(db.t.drop(),None)

class TestJoin(unittest.TestCase):
    def testRun(self):
        db=SQLDB('sqlite:memory:')
        self.assertEqual(db.define_table('t1',db.Field('a'))._db,db)
        self.assertEqual(db.define_table('t2',db.Field('a'),db.Field('b',db.t1))._db,db)
        i1=db.t1.insert(a='1')
        i2=db.t1.insert(a='2')
        i3=db.t1.insert(a='3')
        db.t2.insert(a='4',b=i1)
        db.t2.insert(a='5',b=i2)
        db.t2.insert(a='6',b=i2)
        self.assertEqual(len(db(db.t1.id==db.t2.b).select(orderby=db.t1.a|db.t2.a)),3)
        self.assertEqual(db(db.t1.id==db.t2.b).select(orderby=db.t1.a|db.t2.a)[2].t1.a,'2')
        self.assertEqual(db(db.t1.id==db.t2.b).select(orderby=db.t1.a|db.t2.a)[2].t2.a,'6')
        self.assertEqual(len(db().select(db.t1.ALL,db.t2.ALL,left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a)),4)
        self.assertEqual(db().select(db.t1.ALL,db.t2.ALL,left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a)[2].t1.a,'2')
        self.assertEqual(db().select(db.t1.ALL,db.t2.ALL,left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a)[2].t2.a,'6')
        self.assertEqual(db().select(db.t1.ALL,db.t2.ALL,left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a)[3].t1.a,'3')
        self.assertEqual(db().select(db.t1.ALL,db.t2.ALL,left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a)[3].t2.a,None)
        self.assertEqual(len(db().select(db.t1.ALL,db.t2.id.count(),left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a,groupby=db.t1.a)),3)
        self.assertEqual(db().select(db.t1.ALL,db.t2.id.count(),left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a,groupby=db.t1.a)[0]._extra[db.t2.id.count()],1)
        self.assertEqual(db().select(db.t1.ALL,db.t2.id.count(),left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a,groupby=db.t1.a)[1]._extra[db.t2.id.count()],2)
        self.assertEqual(db().select(db.t1.ALL,db.t2.id.count(),left=db.t2.on(db.t1.id==db.t2.b),orderby=db.t1.a|db.t2.a,groupby=db.t1.a)[2]._extra[db.t2.id.count()],0)
        self.assertEqual(db.t1.drop(),None)
        self.assertEqual(db.t2.drop(),None)

if __name__ == "__main__":
    unittest.main()
    
