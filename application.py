from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CategoryItem

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
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


## Create a state token to prevent request forgery. 
## Store it in the session for later validation. 
@app.route('/login')
def showLogin():
    """
    Creates a random anti-forgery state token with each GET request
    sent to /login 
    """
    state = ''.join(random.choice(string.ascii_uppercase + \
        string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    x = 0
    # Validate state token
    print login_session['state']
    print request.args
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        x += 1
        print x
        return response
    # Obtain authorization code
    x += 1
    print x
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
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    # login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'  
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    # return render_template('login.html', username=login_session['username']) 
    return output


@app.route("/gdisconnect")
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: ' 
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token'] 
        del login_session['gplus_id']
        del login_session['username']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
    
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


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
# @app.route('/catalog', defaults={'username': ''})
# @app.route('/catalog/loggedin/<username>')
@app.route('/catalog')
@app.route('/catalog/loggedin')
def showCatalog():
    """
    A catalog contains a list of all categories in the database. 

    C[R]UD 
    """
    catalog = session.query(Category).all()
    return render_template('catalog.html', catalog=catalog)


@app.route('/catalog/<category_name>')
def showCategory(category_name):
    """
    A category represents a table of items of a specific category. 
    Instead of using a category's ID as the url identifier, using the
    name of a category instead is intended to enhance user readability. 


    C[R]UD 
    """
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(CategoryItem).filter_by(category_id=category.id)
    return render_template(
        'category.html', category=category, items=items)


@app.route('/catalog/<category_name>/<item_name>')
def showCategoryItem(category_name, item_name):
    """
    C[R]UD 
    """
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    return render_template(
        'categoryitem.html', item=item, description=item.description, category=category)


@app.route('/catalog/<category_name>/add', methods=['GET', 'POST'])
def addCategoryItem(category_name):
    """
    Adds an item to a category provided by input values in the
    addcategoryitem.html form. 

    CR[U]D 
    """
    if 'username' not in login_session:
        return redirect('/login')

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
    """
    Edits a category item provided by input values in the
    editcategoryitem.html form. 
    
    CR[U]D 
    """
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
    """
    Deletes a category item upon initiation by user selection of the
    "delete" button/link in the categoryitem.html page which redirects
    to deletecategoryitem.html to request confirmation. 
    
    CRU[D] 
    """
    category = session.query(Category).filter_by(name=category_name).one()
    itemToDelete = session.query(CategoryItem).filter_by(category_id=category.id, name=item_name).one()
    
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showCategory', category_name=category_name))
    else:
        return render_template('deletecategoryitem.html', category=category, item=itemToDelete)


@app.route('/catalog/index', methods=['GET', 'POST'])
def renderIndex():
    catalog = session.query(Category).all()
    return render_template('index.html', catalog=catalog)


@app.route('/catalog/index/<category_name>', methods=['GET', 'POST'])
def renderIndexCategory(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(CategoryItem).filter_by(category_id=category.id)
    return render_template(
        'categoryNew.html', category=category, items=items)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)