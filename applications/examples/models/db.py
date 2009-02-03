#########################################################################
## This scaffolding model makes your app work on Google App Engine too   
#########################################################################

try:
    from gluon.contrib.gql import *         # if running on Google App Engine
except:
    db=SQLDB('sqlite://storage.db')         # if not, use SQLite or other DB
else:
    db=GQLDB()                              # connect to Google BigTable
    session.connect(request,response,db=db) # and store sessions there

db.define_table('users',
                SQLField('name'),
                SQLField('email'))

# ONE (users) TO MANY (dogs)
db.define_table('dogs',
                SQLField('owner_id',db.users),
                SQLField('name'),
                SQLField('type'),
                SQLField('vaccinated','boolean',default=False),
                SQLField('picture','upload',default=''))

db.define_table('products',
                SQLField('name'),
                SQLField('description','text'))

# MANY (users) TO MANY (purchases)
db.define_table('purchases',
                SQLField('buyer_id',db.users),
                SQLField('product_id',db.products),
                SQLField('quantity','integer'))

purchased=((db.users.id==db.purchases.buyer_id)&(db.products.id==db.purchases.product_id))

db.users.name.requires=IS_NOT_EMPTY()
db.users.email.requires=[IS_EMAIL(), IS_NOT_IN_DB(db,'users.email')]
db.dogs.owner_id.requires=IS_IN_DB(db,'users.id','users.name')
db.dogs.name.requires=IS_NOT_EMPTY()
db.dogs.type.requires=IS_IN_SET(['small','medium','large'])
db.purchases.buyer_id.requires=IS_IN_DB(db,'users.id','users.name')
db.purchases.product_id.requires=IS_IN_DB(db,'products.id','products.name')
db.purchases.quantity.requires=IS_INT_IN_RANGE(0,10)
