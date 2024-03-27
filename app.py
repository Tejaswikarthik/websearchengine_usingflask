from flask import Flask, render_template, request, session , redirect , g , url_for, jsonify
from search import search
from filter import Filter
from storage import DBStorage
import html
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
from werkzeug.security import generate_password_hash, check_password_hash
# import pyttsx3

# engine = pyttsx3.init()
# text = "Welcome user "

# engine.say(text)

# engine.runAndWait()




app = Flask(__name__)
app.secret_key = '2345TEJA'

connection = sqlite3.connect("user_data.db")
cursor = connection.cursor()
command = """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0
    )"""
cursor.execute(command)
connection.commit()



styles = """
<script>
const relevant = function(query, link){
    fetch("/relevant", {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
           "query": query,
           "link": link
          })
        });
}

</script>
"""



result_template = """
<div style = "justify-content: left">
<p class="site">{rank}: {link} <span class="rel-button" onclick='relevant("{query}", "{link}");'>Relevant</span></p>
<a href="{link}">{title}</a>
<p class="snippet">{snippet}</p><br>
</div>
"""

def show_search_form():
    try:
        if session['user']:
            user = session.get('user')
            if user['is_admin']:
                return render_template('admin_view.html')
            return render_template('Search_user.html')
    except:
        pass
    return render_template('Search.html')
def run_search(query):
    g.query1 = query
    
    try:
        if session['user']:
            user = session.get('user')
            connection = sqlite3.connect("user_data.db")
            cursor = connection.cursor()
            command = """CREATE TABLE IF NOT EXISTS users_history(email TEXT,query TEXT)"""
            cursor.execute(command)
            command1 = """INSERT INTO users_history(email,query) VALUES (?,?)"""
            cursor.execute(command1,(user['email'],query))
            connection.commit()
            connection.close()

    except:
        pass
    
    results = search(query)
    fi = Filter(results)
    filtered = fi.filter()
    try:
        if session['user']:
            rendered = render_template('user_results.html')
    except:
        rendered = render_template('blank.html')
    filtered["snippet"] = filtered["snippet"].apply(lambda x: html.escape(x))
    for index, row in filtered.iterrows():
        rendered += result_template.format(**row)
    return rendered

@app.route("/", methods=['GET', 'POST'])
@app.route("/search",methods = ['GET','POST'])
def search_form():
    if request.method == 'POST':
        query = request.form["query"]
        return run_search(query)
    else:
        return show_search_form()

@app.route("/relevant", methods=["POST"])
def mark_relevant():
    data = request.get_json()
    query = data["query"]
    link = data["link"]
    storage = DBStorage()
    storage.update_relevance(query, link, 10)
    return jsonify(success=True)
@app.route('/register',methods=['GET','POST'])

def register():
    
    if request.method == 'POST':
        
        con = sqlite3.connect("user_data.db")
        cur = con.cursor()
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        command = """SELECT * FROM users WHERE email = '{email}' AND password = '{password}'"""
        cur.execute(command)
        data = cur.fetchone()
    
        if data:
            return render_template('error.html')
        
        if not data:
            command1 ="""INSERT INTO users(name,email,password) VALUES(?,?,?)"""
            cur.execute(command1,(name,email,hashed_password))
            con.commit()
            con.close()
            return render_template('login.html')

    return render_template('register.html')
    

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("user_data.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        data = cur.fetchone()
        conn.close()
        if data and check_password_hash(data[3], password):
            session['user'] = {
                'name': data[1],
                'email': data[2],
                'is_admin': bool(data[4])
            }
            return redirect(url_for('welcome'))
        else:
            return render_template('invalid.html')
    return render_template('login.html')

@app.route('/welcome',methods=['GET','POST'])

def welcome():
    if g.user:
        user = session.get('user')
        print(user)
        return render_template('welcome.html',user = user['name'])
    return redirect(url_for('login'))

@app.before_request
def before_request():
    g.user = None

    if 'user' in session:
        g.user = session['user']

@app.route('/dropsession',methods = ['GET','POST'])
def dropsession():
    try:
        if session['user']:
            user = session['user']
            session.pop('user')
            return render_template('dropped.html')
    except:
        return render_template('error.html')

@app.route('/history',methods = ["GET","POST"])
def history():
    user = session.get('user')
    connection = sqlite3.connect("user_data.db")
    cursor = connection.cursor()
    command = f"SELECT query FROM users_history WHERE email = '{user['email']}' ;"
    cursor.execute(command)
    history_data = cursor.fetchall()
    connection.commit()
    connection.close()
    return render_template('history.html',data= history_data)
@app.route('/users',methods = ["GET","POST"])
def users():
    user = session.get('user')
    if user['is_admin']:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name,email FROM users")
        users = cursor.fetchall()
        conn.close()
        return render_template('show.html', users=users)
    else:
        return render_template('unauthorised.html',users=0)

    

@app.route('/changepassword',methods = ["GET","POST"])
def  changepassword():  
    if request.method == 'POST':
        con = sqlite3.connect("user_data.db")
        cur = con.cursor()
        email = request.form['email']
        password = request.form['password']
        newpassword = request.form['newpassword']
        hashed_password = generate_password_hash(newpassword)
        command = f"UPDATE users SET password = ? WHERE email = ? ;"
        cur.execute(command,(hashed_password,email))
        con.commit()
        con.close()
        return render_template('login.html')
    return render_template('changepwd.html')

@app.route("/dashboard",methods=["GET","POST"])

def dashboard():
    user = session.get('user')
    if user['is_admin']:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT query FROM users_history")
        data = cursor.fetchall()
        conn.close()
        counts = {}
        for entry in data:
            if entry[0] in counts:
                counts[entry[0]] += 1
            else:
                counts[entry[0]] = 1

        plt.figure(figsize=(6, 4))
        plt.pie(counts.values(), labels=counts.keys(), autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

    
        chart_data = base64.b64encode(buffer.getvalue()).decode()

        return render_template('chart.html', chart_data=chart_data)
    else:
        return render_template('unauthorised.html')

    

@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.get_json()
    email = data.get('email')
    if email:
        conn = sqlite3.connect('user_data.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email=?", (email,))
        cursor.execute("DELETE FROM users_history WHERE email=?", (email,))
        conn.commit()
        conn.close()
        return "User deleted successfully", 200
    else:
        return "Invalid request", 400



@app.route('/dashboard_user',methods=['GET','POST'])  
def dashboard_user():
    pass   
