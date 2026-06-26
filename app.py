from flask import Flask, render_template, request, url_for, redirect
import pandas as pd
from sqlalchemy import create_engine

app = Flask(__name__)


@app.route("/")
def lipat():
    return redirect('/home')


@app.route('/home')
def home():
    return render_template('Homepage.html')


if __name__ == '__main__':
    app.run(debug=True)
