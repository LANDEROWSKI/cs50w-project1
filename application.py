import os
import requests

from flask import Flask, session, render_template, redirect, request, jsonify, url_for, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from sesion import login_required

app = Flask(__name__)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        if not user or not password:
            mensaje = 'campos vacios'
            return render_template('error.html', MESSAGE=mensaje)


        print(password)

        rows = db.execute(
            text("SELECT * FROM users WHERE username=:username"), {'username': user}).fetchall()
        print(len(rows))

        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            mensaje = 'Correo y Contraseña Incorrecta!'
            return render_template('error.html', MESSAGE=mensaje)

        session['user_id'] = rows[0][0]
        session['username'] = rows[0][1]

        return render_template("index.html")
    else:
        return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registrar():
    if request.method == 'POST':

        usuario = request.form['usuario']
        password = request.form['password']
        passwordTrue = request.form['passwordTrue']

        hash_pass = generate_password_hash(password)

        if not usuario or not password:
            mensaje = 'Por favor rellene todos los campos'
            return render_template('error.html', MESSAGE=mensaje)
        elif not passwordTrue:
            mensaje = 'Debe confirmar contrasenia'
            return render_template('error.html', MESSAGE=mensaje)
        elif password != passwordTrue:
            mensaje = 'Contrasenia no coinciden'
            return render_template('error.html', MESSAGE=mensaje)

        checkUser = db.execute(text("SELECT * FROM users WHERE username = :username"),
                               {"username": usuario}).fetchall()

        if len(checkUser) != 0:
            return ("Usuario no disponible"), 400

        db.execute(text('INSERT INTO users(username,password) values(:username, :password)'), {
                   'username': usuario, 'password': hash_pass})
        db.commit()

        return render_template("login.html")

    else:
        return render_template("registro.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/buscar", methods=["GET", "POST"])
@login_required
def buscar():

    if request.method == 'POST':
        search = request.form.get('buscar')

        # Este metodo 'title' vuelve todas las letras de cada palbra en mayuscula
        search = search.title()

        libros = db.execute(text(f"""SELECT * FROM books WHERE title LIKE '%{search}%' OR 
        author LIKE '%{search}%' OR isbn LIKE '%{search}%'"""))

        if libros.rowcount == 0:
            return render_template('resultados.html', existe=False)

        libros = libros.fetchall()

       

        return render_template('resultados.html', books=libros, existe=True)

    else:

        return render_template('buscar.html')


@app.route("/libro/<isbn>", methods=['GET', 'POST'])
@login_required
def libro(isbn):
    if request.method == 'POST':

        califi = int(request.form.get('rating'))
        descrip = request.form.get('descrip')

        # Obtener ID del librop
        id_libro = db.execute(text("SELECT id_libros FROM books WHERE isbn = :isbn"),
                              {"isbn": isbn}).fetchone()
        id_libro = id_libro[0]

        # Se verifica que el usuario actual solo haya reseñado una vez este libro
        resenias = db.execute(text("SELECT * FROM reviews WHERE id_user = :id_user AND id_book = :id_book"),
                              {"id_user": session['user_id'],
                               "id_book": id_libro})

        if resenias.rowcount != 0:
            flash("Ya has dado tu resenia", "danger")
            return redirect("/libro/" + isbn)

        # Si el usuario aun no ha dado una resenia se guarda
        db.execute(text("""INSERT INTO reviews (rating, description, id_user, id_book) VALUES 
                    (:rating, :description, :id_user, :id_book)"""),
                   {"rating": califi,
                    "description": descrip,
                    "id_user": session['user_id'],
                    "id_book": id_libro})

        db.commit()

        flash("Reseña Guardada Exitosamente", "success")
        return redirect("/libro/" + isbn)
    else:
        datosLibro = db.execute(
            text("SELECT isbn, title, author, year FROM books WHERE isbn=:isbn"), {'isbn': isbn})
        datosLibro = datosLibro.fetchall()

        libroGR = requests.get(
            "https://www.googleapis.com/books/v1/volumes?q=isbn:"+isbn).json()
        libroGR = libroGR['items']
        libroGR = libroGR[0]['volumeInfo']
        
        id_libro = db.execute(text("SELECT id_libros FROM books WHERE isbn = :isbn"),
                              {"isbn": isbn}).fetchone()
        id_libro = id_libro[0]

        resenias = db.execute(text(f""" SELECT U.username, description, rating FROM reviews AS R 
                                    INNER JOIN users AS U 
                                    ON U.id=R.id_user WHERE R.id_book={id_libro}""")).fetchall()
        
        return render_template('libro.html', datosLibro=datosLibro, libroGR=libroGR, reviews=resenias)


@app.route('/api/<isbn>', methods=['GET'])
def api(isbn):

    # Consulta de todos los datos para el JSON
    consulta = db.execute(text("""
        SELECT title, author, isbn, year, COUNT(R.id_resenias) AS review_count, AVG(R.calificacion) AS average_score 
        FROM books AS L
        INNER JOIN reviewa AS R ON L.id_libros=R.id_book
        WHERE isbn=:isbn
        GROUP BY title, author, isbn, year
    """), {'isbn': isbn}).fetchone()

    if consulta is None:
        return jsonify({'Posibles Errores': {'Error ISBN': 'ISBN ingresada Invalida',
                                             'Libro': 'Este libro no tiene resenias'}}), 404

    # convertir a dict
    consulta = dict(consulta)

    # dar formato para mostrar dos decimales
    consulta['average_score'] = float('%.2f' % (consulta['average_score']))

    return jsonify(consulta)


if __name__ == "__main__":
    app.run()
