import csv
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def cargar():
    f = open("books.csv")
    filas = csv.reader(f)

    # crear tabla
    for isbn, title, author, year in filas:
        db.execute(text("INSERT INTO book (isbn,title,author,year) VALUES (:isbn, :title, :author, :year)"),
                   {"isbn": isbn, "title": title, "author": author, "year": int(year)})
        print(isbn, title, author, year, sep=" -*- ")

    db.commit()


def main():
    cargar()


if __name__ == "__main__":
    main()