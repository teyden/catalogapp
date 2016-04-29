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

"""
Category
	- name 
CategoryItem 
	- name
	- description
	- image_url
	- category  (a foreign key to a Category)
"""

character_adjectives = ["feisty", "playful", "fun", "adorable", "huggable", "bright", "smart", "brave", "cute", "expressive", "sweet", "well-behaved"]
names = ["Henry", "Rakki", "Lucky", "George", "Looshy", "Panda", "Jerrie", "Teddy", "Ron"]
maltese_images = ["http://www.dogbreedinfo.com/images26/MaltesePurebredDogPuppyGroomWhiteTanBrownRustLightIvoryColorLatte3Years1.jpg", \
"https://upload.wikimedia.org/wikipedia/commons/c/c4/Emily_Maltese.jpg", \
"http://animalsbreeds.com/wp-content/uploads/2014/10/Maltese.jpg", \
"https://i.ytimg.com/vi/DmFK4Uz4aYY/maxresdefault.jpg", \
"http://www.dogbreedinfo.com/images26/MaltesePurebredDogBentley1YearOld2.jpg", \
"http://www.localpuppybreeders.com/wp-content/uploads/photo-gallery/Maltese/shutterstock_174588677.jpg"]

CATEGORY_SEED = { "name": "", "description": "", "image_url": "", "category": ""}
def validFields(obj, seed=CATEGORY_SEED):
	"""
	Returns True if all match the seed, else False.
	"""
	valid = True
	for field in CATEGORY_SEED:
		if field not in obj:
			valid = False
			break 
	if valid:
		if isinstance(obj["category"], Category):
			return True 
	return False


def addDog(session, info):
	"""
	Adds a new dog to its breed category, given by the "category" field in info 

	INPUT:
		info - a dict with name, description, image_url, and category 
	"""
	if validFields(info):
		category_item = CategoryItem(name=info["name"], 
			description=info["description"], 
			image_url=info["image_url"], 
			category=info["category"])
		session.add(category_item)
		session.commit()
	else:
		print "Invalid fields. Did not add new object."


import numpy as np 

L = len(character_adjectives)
Maltese = Category(name="Maltese")
malteses = []
for i, image in enumerate(maltese_images):
	newMaltese = {}
	newMaltese["image_url"] = image 
	newMaltese["name"] = names[i] 
	x = 0
	description = ""
	while x < 3:
		k = np.random.randint(np.random.randint(0, L/2), np.random.randint(L/2+1, L-1))
		description += character_adjectives[k] + ", "
		x += 1
	description = description[:-2] + "."
	newMaltese["description"] = description
	newMaltese["category"] = Maltese
	malteses += [newMaltese]


for dog in malteses:
	addDog(session, dog) 

session.close() 


# # Random Category
# category1 = Category(name="Maltese")
# session.add(category1)
# session.commit() 

# categoryitem1 = CategoryItem(name="Henry", description="", image_url="https://upload.wikimedia.org/wikipedia/commons/c/c4/Emily_Maltese.jpg",
#                      category=category1)
# session.add(categoryitem1)
# session.commit()


# categoryitem2 = CategoryItem(name="Rakki", description="Cute, ", image_url="http://",
#                      category=category1)
# session.add(categoryitem2)
# session.commit()

# categoryitem3 = CategoryItem(name="MoreThings", description="On the stairs", image_url="http://", category=category1)
# session.add(category3)
# session.commit()


# # Socks Category
# category2 = Category(name="Socks")
# session.add(category2)
# session.commit()

# categoryitem1 = CategoryItem(name="Funky", description="", image_url="", category=category2)
# session.add(categoryitem1)
# session.commit() 


# print "added category items!"


# for category in session.query(Category):
#        print category.id 