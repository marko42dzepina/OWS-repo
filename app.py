from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha512_crypt
from functools import wraps


app = Flask(__name__)

# mySQL konfiguracija
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask projekt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# MYSQL inicijalizacija
mysql = MySQL(app)

# Index
@app.route('/')
def index():
    return render_template("home.html")

# O stranici
@app.route('/about')
def about():
    return render_template("about.html")

# Članci
@app.route('/articles')
def articles():

    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM clanci")
    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    cur.close()

# Pojedinačni članak
@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM clanci WHERE id = %s", [id])
    article = cur.fetchone()
    return render_template('article.html', article=article)

# Klasa za registraciju
class RegisterForm(Form):
    name = StringField("Name", [validators.Length(min = 1, max = 50)])
    username = StringField("Username", [validators.Length(min = 4, max = 25)])
    email = StringField("Email", [validators.Length(min = 6, max = 50)])
    password = PasswordField("Password", [validators.DataRequired(), validators.EqualTo("confirm", message="Passwords do not match")])
    confirm = PasswordField("Confirm password")

# Registracija korisnika u bazu
@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha512_crypt.encrypt(str(form.password.data))
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO korisnici(name,email,username,password) VALUES (%s, %s, %s, %s)", (name, email, username, password))
        mysql.connection.commit()
        cur.close()
        flash("Successful registration, please log in", "success")
        redirect(url_for("index"))
    return render_template('register.html', form=form)

# Login korisnika
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM korisnici WHERE username = %s", [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            # Uspoređuje lozinke
            if sha512_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')

# Provjerava dali je korisnik ulogiran
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You are now logged out","success")
    return redirect(url_for('login'))

# Kontrolna ploča
@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM clanci")
    articles = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html' ,articles = articles)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg = msg)
    cur.close()

# Klasa za formu članka
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# Dodavanje članka
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO clanci(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))
        mysql.connection.commit()
        cur.close()
        flash('Article successfully created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)

# Editiranje članka u bazi
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()
    # Dohvaća članak iz baze
    result = cur.execute("SELECT * FROM clanci WHERE id = %s", [id])
    article = cur.fetchone()
    cur.close()
    form = ArticleForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        cur = mysql.connection.cursor()
        app.logger.info(title)
        cur.execute ("UPDATE clanci SET title=%s, body=%s WHERE id=%s",(title, body, id))
        mysql.connection.commit()
        cur.close()
        flash('Article successfully updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)

# Brisanje članka iz baze
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM clanci WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('Article successfully deleted', 'success')
    return redirect(url_for('dashboard'))

# Main
if __name__ == "__main__":
    app.secret_key="secret123"
    app.run(host='127.0.0.1', port=5000, debug=1)
