import os, requests

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask import Flask, render_template, request, session, redirect, url_for, g, jsonify
from flask_session import Session

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
	    session.pop('user', None)
	if 'user' in session:
		return redirect(url_for('user'))
	return render_template("index.html")

@app.route("/registration")
def registration():
	return render_template("registration.html")


@app.route("/reg", methods=["POST"])
def reg():
	username = request.form.get("username")
	password = request.form.get("password")
	login = db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
	db.commit()
	return render_template("success.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form.get("username")
		password = request.form.get("password")
		login = db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).fetchall()
		if login == []:
			return render_template("bad.html")
		else:
			session['user'] = username.capitalize()
			#session['id'] = login.id
			return redirect(url_for('user'))

	return render_template("login.html")

@app.route("/user", methods=["GET", "POST"])
def user():
	if g.user:
		return render_template("user.html", username=session.get('user', ''))

	return redirect(url_for("index"))
		#return session.get('user', '') #

@app.route("/books", methods=["post"])
def books():
	f = request.form.get("from")
	t = request.form.get("to")
	books = db.execute("SELECT * FROM books WHERE year >= :f AND year <= :t", {"f": f, "t": t}).fetchall()
	return render_template("books.html", books=books)

@app.route("/books/<book_id>", methods=["GET", "POST"])
def book(book_id):
	#add review
	if request.method == "POST" and 'user' in session:
		username = session['user']
		isbn = book_id
		text = request.form.get("text")
		db.execute("INSERT INTO reviews (isbn, name, text) VALUES (:isbn, :name, :text)", {"isbn": isbn, "name": username, "text": text})
		db.commit()
	#reviews
	reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": book_id}).fetchall()
	#info from api
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "09qTaejfjua5WHx4C4dMQ", "isbns": book_id})
	if res.status_code == 200:
		data = res.json()
	#info from db
	book = db.execute("SELECT * FROM books WHERE isbn = :book_id", {"book_id": book_id}).fetchone()
	return render_template("book.html", book=book, data=data['books'][0]['average_rating'], rev=data['books'][0]['reviews_count'], reviews=reviews)

@app.route("/api/books/<book_id>")
def api_book(book_id):
	book = db.execute("SELECT * FROM books WHERE isbn = :book_id", {"book_id": book_id}).fetchone()
	if book is None:
		return jsonify({"error": "Invalid flight_id"}), 422
	return jsonify({
		"isbn": book.isbn,
		"author": book.author,
		"title": book.title,
		"year": book.year
		})

@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']


@app.route('/dropsession')
def dropsession():
    session.pop('user', None)
    return 'Dropped!'