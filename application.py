from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CategoryItem

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


## API Endpoints (JSON, XML, RSS, Atom)
@app.route('/catalog/JSON')
def catalogJSON():
    catalog = session.query(Category).all()
    return jsonify(Catalog=[i.serialize for i in catalog])


@app.route('/catalog/<category_name>/JSON')
def categoryItemsJSON(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(CategoryItem).filter_by(category_id=category.id).all()
    return jsonify(CategoryItems=[i.serialize for i in items])


@app.route('/catalog/<category_name>/<item_name>/JSON')
def categoryItemJSON(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    return jsonify(CategoryItem=item.serialize)


## Routing
@app.route('/')
@app.route('/catalog')
def showCatalog():
    """
    A catalog contains a list of all categories in the database. 
    """
    catalog = session.query(Category).all()
    return render_template('catalog.html', catalog=catalog)


@app.route('/catalog/<category_name>')
def showCategory(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(CategoryItem).filter_by(category_id=category.id)
    return render_template(
        'category.html', category=category, items=items)


@app.route('/catalog/<category_name>/<item_name>')
def showCategoryItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    return render_template(
        'categoryitem.html', item=item, description=item.description, category=category)


@app.route('/catalog/<category_name>/add', methods=['GET', 'POST'])
def addCategoryItem(category_name):
    category = session.query(Category).filter_by(name=category_name).one()

    if request.method == 'POST':
        newItem = CategoryItem(name=request.form['name'], description=request.form[
                           'description'], image_url=request.form['image_url'], category_id=category.id)
        session.add(newItem)
        session.commit()
        flash("new catagory item created!")
        ## After submitting new item, redirects back to main page.
        return redirect(url_for('showCategory', category_name=category_name))
    else:
        return render_template('addcategoryitem.html', category=category)


@app.route('/catalog/<category_name>/<item_name>/edit', methods=['GET', 'POST'])
def editCategoryItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    editedItem = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['image_url']:
            editedItem.image_url = request.form['image_url']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showCategory', category_name=category_name))
    else:
        return render_template(
            'editcategoryitem.html', category=category, item=editedItem)


@app.route('/catalog/<category_name>/<item_name>/delete', methods=['GET', 'POST'])
def deleteCategoryItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    itemToDelete = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    print itemToDelete
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showCategory', category_name=category_name))
    else:
        return render_template('deletecategoryitem.html', category=category, item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)