from flask import Flask, render_template, request, session, redirect, flash, send_file
import sys
import os
import re
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import pandas as pd
import numpy as np 
from datetime import date
import urllib.request

app = Flask(__name__)
bcrypt = Bcrypt()

client = MongoClient("mongodb+srv://RagulSV:ragulsv123@cluster0-dv7bc.mongodb.net/test?retryWrites=true&w=majority")
db = client.get_database('Emergency_Food_Helpline')
user = db.User

# Home Page
@app.route('/',methods=['GET'])
def start():
    session['logged_in']= False
    session['username'] = None
    return redirect('/home')

@app.route('/home', methods=['GET'])
def index():
    if session['logged_in']:
        flash('You are logged in as ' + session['username'], 'danger')
    return render_template('homepage.html')

# Login Page
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        userDetails=request.form
        username=userDetails['username']
        password=userDetails['password']
        login_user = user.find_one({'username' : request.form['username']})
        if login_user:
            if bcrypt.check_password_hash(login_user['password'],password):
                session['logged_in'] = True
                session['username'] = username
                if login_user['type']=='Customer':
                    session['type']='Customer'
                    flash('You are now logged in','success')
                    return redirect('/customer')
                else:
                    session['type']='Staff'
                    flash('You are now logged in','success')
                    return redirect('/staff')
            flash('Invalid username/password combination','danger')
            return redirect('/login')
        flash('Username does not exist. Register First!!','danger')
        return redirect('/login')
    else:
        if session['logged_in']:
            flash('You are logged in as ' + session['username'],'warning')
        return render_template('login.html')
    
#Register Page
def validate(user):
    e=0
    #check password
    regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')    
    if(regex.search(user['password']) == None): 
        e+=1 
        flash('Password should contain a special character!!','warning')
    if not any(x.isupper() for x in user['password']):
        e+=1
        flash('Password should contain atleast one UpperCase letter!!','warning')     
    if not any(x.isdigit() for x in user['password']):
        e+=1
        flash('Password should contain atleast one number!!','warning')
    #check email
    regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
    if not re.search(regex,user['email']):  
        e+=1
        flash('Not a Vaild Email!!','warning')

    if e==0:
        return True
    else:
        return False


@app.route('/register',methods=['GET'])
def register():
    if session['logged_in']:
        flash('You are logged in as ' + session['username'],'warning')
        return redirect('/home')
    return render_template('register.html')

@app.route('/regcust',methods=['GET','POST'])
def register_customer():
    if request.method == 'POST':
        existing_user = user.find_one({'username': request.form['username']})
        if existing_user is None:
            if validate(request.form):
                username = request.form['username']
                password = request.form['password']
                hashpass = bcrypt.generate_password_hash(password)
                email = request.form['email']
                types = 'Customer'
                orders = []
                user.insert_one({'username': username,'password': hashpass,'email':email,'type':types, 'orders':orders})
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in','success')
                return redirect('/customer')
            else:
                return redirect('regcust')
            
        flash('That username already exists!','danger')
        return redirect('/regcust')
    
    if session['logged_in']:
            flash('You are logged in as ' + session['username'],'warning')
    return render_template('regcust.html')

@app.route('/regstaff',methods=['GET','POST'])
def register_staff():
    if request.method == 'POST':
        existing_user = user.find_one({'username' : request.form['username']})
        if existing_user is None:
            if validate(request.form):
                staffID = request.form['staffid']
                username = request.form['username']
                password = request.form['password']
                hashpass = bcrypt.generate_password_hash(password)
                email = request.form['email']
                city = request.form['city']
                types = 'Staff'
                orders = []
                prev_orders = []
                user.insert_one({'staffid':staffID,'username' : username, 'password' : hashpass, 'email':email,'city':city, 'type':types,'orders':orders,'prev_orders':prev_orders})
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in','success')
                return redirect('/staff')
            else:
                return redirect('regstaff')
        flash('That username already exists!','danger')
        return redirect('/regstaff')
    
    if session['logged_in']:
            flash('You are logged in as ' + session['username'],'warning')
    return render_template('regstaff.html')

#Customer Dashboard
@app.route('/customer',methods=['GET','POST'])
def customer_dash():
    if request.method == 'POST':
        place_order = {"date":str(date.today()),"name":session['username'],"address":request.form['address'],"order": request.form['order']}
        existing_user = user.find_one({'city' : request.form['city']})
        if existing_user:
            user.update_one( {"username":existing_user['username']}, {"$push": { "orders":place_order}}) 
            user.update_one( {"username":existing_user['username']}, {"$push": { "prev_orders":place_order}}) 
            flash('Your Order is sent successfully!!','success')
            return redirect('/customer')
        flash('City is not currently Available!!','danger')
        return redirect('/customer')
    
    existing_user = user.find_one({'username' : session['username']})
    if session['logged_in'] and existing_user['type']=='Customer':
        return render_template('custdash.html')
    else:
        flash("You cannot access the Customer dashboard!! Login as a Customer","danger")
        return redirect("/home")
    
#Staff Dashboard
@app.route('/staff',methods=['GET','POST'])
def staff_dash():
    if request.method == 'POST':
        confirm_order = request.form['order']
        user.update_one( {"username":session['username']}, {"$pull": {"orders":{"name":confirm_order}}})
        return redirect('/staff')
    existing_user = user.find_one({'username' : session['username']})
    if session['logged_in'] and existing_user['type']=='Staff':
        city = existing_user['city']
        orders = existing_user['orders']
        return render_template('staffdash.html',orders=orders,city=city)
    elif not session['logged_in']:
        flash("You are not Logged in","danger")
        return redirect("/home")
    else:
        flash("You cannot access the Staff dashboard!! Login as a Staff","danger")
        return redirect("/home")
    
#Staff Dashboard
@app.route('/prev',methods=['GET'])
def previous_orders():
    existing_user = user.find_one({'username' : session['username']})
    if session['logged_in'] and existing_user['type']=='Staff':
        city = existing_user['city']
        prev_orders = existing_user['prev_orders']
        return render_template('prev_orders.html',prev_orders=prev_orders,city=city)
    elif not session['logged_in']:
        flash("You are not Logged in","danger")
        return redirect("/home")
    else:
        flash("You cannot access the Staff dashboard!! Login as a Staff","danger")
        return redirect("/home")

@app.route('/hotline',methods=['GET'])
def show_hotlines():
    existing_user = user.find_one({'username' : session['username']})
    if session['logged_in'] and existing_user['type']=='Customer':
        return render_template('hotlines.html')
    elif not session['logged_in']:
        flash("You are not Logged in","danger")
        return redirect("/home")
    else:
        flash("You cannot access the Customer dashboard!! Login as a Customer","danger")
        return redirect("/home")    
    
@app.route('/logout',methods=['GET'])
def logout():
    session['logged_in'] = False
    session['username'] = None
    flash('You are logged out','danger')
    return redirect('/home')

if __name__ == '__main__':
    app.secret_key = 'youcantseeme'
    # port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=int(sys.argv[1]))