dba=SQLDB('sqlite://tests.db')
      
dba.define_table('users',
                SQLField('name'),
                SQLField('email'))

# ONE (users) TO MANY (dogs)
dba.define_table('dogs',
                SQLField('owner_id',dba.users),
                SQLField('name'),                
                SQLField('type'),
                SQLField('vaccinated','boolean',default=False),
                SQLField('picture','upload',default=''))

dba.define_table('products',
                SQLField('name'),
                SQLField('description','text'))

# MANY (users) TO MANY (purchases)
dba.define_table('purchases',
                SQLField('buyer_id',dba.users),
                SQLField('product_id',dba.products),
                SQLField('quantity','integer'))

purchased=((dba.users.id==dba.purchases.buyer_id)&(dba.products.id==dba.purchases.product_id))

dba.users.name.requires=IS_NOT_EMPTY()
dba.users.email.requires=[IS_EMAIL(), IS_NOT_IN_DB(dba,'users.email')]
dba.dogs.owner_id.requires=IS_IN_DB(dba,'users.id','users.name')
dba.dogs.name.requires=IS_NOT_EMPTY()
dba.dogs.type.requires=IS_IN_SET(['small','medium','large'])
dba.purchases.buyer_id.requires=IS_IN_DB(dba,'users.id','users.name')
dba.purchases.product_id.requires=IS_IN_DB(dba,'products.id','products.name')
dba.purchases.quantity.requires=IS_INT_IN_RANGE(0,10)