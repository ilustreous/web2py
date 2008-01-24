db=SQLDB('sqlite://images.db')
db.define_table('image',SQLField('file','upload'))