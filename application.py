import os
import requests

from flask import Flask, session, render_template, redirect, request, jsonify
#from helpers import login_required
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template('login.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        if not user or not password:
            return ("Por favor rellene todos los campos"), 400

        # print(correo)
        # print(password)

        rows = db.execute(
            text("SELECT * FROM users WHERE username=:username"), {'username':user}).fetchall()
        # print(rows)

        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            return ("Usuario y/o contraseña inválidos"), 400

        session['user_id'] = rows[0][0]
        session['username'] = rows[0][1]

        return render_template("index.html")
    else:
        return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registrar():
    if request.method == 'POST':
        # obtener datos
        usuario = request.form['usuario']
        password = request.form['password']
        passwordTrue = request.form['passwordTrue']

        hash_pass = generate_password_hash(password)

        if not usuario or not password:
            return ("Por favor rellene todos los campos"), 400
        elif not passwordTrue:
            return ("Debe confirmar contraseña"), 400
        elif password != passwordTrue:
            return ("Contraseñas no coinciden"), 400

        checkUser = db.execute(text("SELECT * FROM users WHERE username = :username"),
                               {"username": usuario}).fetchall()

        if len(checkUser) != 0:
            return ("Usuario no disponible"), 400

        db.execute(text(f"""
            INSERT INTO "users" (username, password)
            VALUES ('{usuario}','{hash_pass}')
        """))
        db.commit()

        return redirect("/")

    else:
        return render_template("registro.html")



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))