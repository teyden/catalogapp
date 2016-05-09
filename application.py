from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CategoryItem, User

app = Flask(__name__)


## OAuth Imports
from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"


## Connect to DB and create DB session
engine = create_engine('sqlite:///catalog2.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


## Helper Functions
def loggedIn():
    if login_session['user_id'] is not None:
        return True 
    else:
        return False


def createUser(login_session):
    """
    Creates a new user if the user doesn't already exist in the DB. 
    """
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


## GOOGLE OAUTH
@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        flash("Current user is already connected.")
        print login_session
        return response 

    print "ACCESS_TOKEN:", access_token
    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        print login_session
        login_session.clear()
        print login_session
        return redirect(url_for('showCatalog'))


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

    C[R]UD 
    """
    catalog = session.query(Category).all()
    items = []
    for category in catalog:
        items += session.query(CategoryItem).filter_by(category_id=category.id).all()
    return render_template('catalog.html', catalog=catalog, items=items, login_session=login_session)


@app.route('/catalog/<category_name>')
def showCategory(category_name):
    """
    A category represents a table of items of a specific category. 
    Instead of using a category's ID as the url identifier, using the
    name of a category instead is intended to enhance user readability. 

    C[R]UD 
    """
    catalog = session.query(Category).all()
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(CategoryItem).filter_by(category_id=category.id)
    # creator = getUserInfo(category.user_id)
    # print creator

    if 'user_id' not in login_session:
        login_session['user_id'] = None 

    return render_template(
        'category.html', catalog=catalog, category=category, items=items, login_session=login_session)


@app.route('/catalog/<category_id>/<item_name>')
def showCategoryItem(category_id, item_name):
    """
    C[R]UD 
    """
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()

    if 'user_id' not in login_session:
        login_session['user_id'] = None 

    return render_template(
        'categoryitem.html', item=item, description=item.description, category=category, login_session=login_session)


@app.route('/catalog/<category_name>/add', methods=['GET', 'POST'])
def addCategoryItem(category_name):
    """
    Adds an item to a category provided by input values in the
    addcategoryitem.html form. 

    [C]RUD 
    """
    if not loggedIn():
        return redirect(url_for('showLogin'))

    category = session.query(Category).filter_by(name=category_name).one()

    if request.method == 'POST':
        newItem = CategoryItem(name=request.form['name'], description=request.form[
                           'description'], image_url=request.form['image_url'], category_id=category.id,
                           item_type=request.form['image_url'], user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New category item (%s) created." % request.form['name'])
        ## After submitting new item, redirects back to main page.
        return redirect(url_for('showCategory', category_name=category_name, login_session=login_session))
    else:
        return render_template('addcategoryitem.html', category=category, login_session=login_session)


@app.route('/catalog/<category_name>/<item_name>/edit', methods=['GET', 'POST'])
def editCategoryItem(category_name, item_name):
    """
    Edits a category item provided by input values in the
    editcategoryitem.html form. 
    
    CR[U]D 
    """
    if not loggedIn():
        return redirect(url_for('showLogin'))

    print login_session

    category = session.query(Category).filter_by(name=category_name).one()
    editedItem = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['image_url']:
            editedItem.image_url = request.form['image_url']
        if request.form['item_type']:
            editedItem.item_type = request.form['item_type']
        session.add(editedItem)
        session.commit()
        flash("Category item (%s) edited." % item_name)
        return redirect(url_for('showCategory', category_name=category_name, login_session=login_session))
    else:
        return render_template(
            'editcategoryitem.html', category=category, item=editedItem, login_session=login_session)


@app.route('/catalog/<category_name>/<item_name>/delete', methods=['GET', 'POST'])
def deleteCategoryItem(category_name, item_name):
    """
    Deletes a category item upon initiation by user selection of the
    "delete" button/link in the categoryitem.html page which redirects
    to deletecategoryitem.html to request confirmation. 
    
    CRU[D] 
    """
    if not loggedIn():
        return redirect(url_for('showLogin'))

    category = session.query(Category).filter_by(name=category_name).one()
    itemToDelete = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    
    if itemToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to do this.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Category item (%s) deleted." % item_name)
        return redirect(url_for('showCategory', category_name=category_name, login_session=login_session))
    else:
        return render_template('deletecategoryitem.html', category=category, item=itemToDelete, login_session=login_session)



if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)