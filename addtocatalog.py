from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Category, CategoryItem

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Random Category
category1 = Category(name="Random")
session.add(category1)
session.commit() 

categoryitem1 = CategoryItem(name="Particles", description="are everywhere", image_url="http://",
                     category=category1)
session.add(categoryitem1)
session.commit()


categoryitem2 = CategoryItem(name="Stuff", description="eeeverywhere", image_url="http://",
                     category=category1)
session.add(categoryitem2)
session.commit()

categoryitem3 = CategoryItem(name="MoreThings", description="On the stairs", image_url="http://", category=category1)
session.add(category3)
session.commit()


# Socks Category
category2 = Category(name="Socks")
session.add(category2)
session.commit()

categoryitem1 = CategoryItem(name="Funky", description="", image_url="", category=category2)
session.add(categoryitem1)
session.commit() 


print "added category items!"


for category in session.query(Category):
       print category.id 