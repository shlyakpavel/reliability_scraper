import os

from parser import yargy_parser
from parser import finding_num

from sqlalchemy import select, create_engine, insert
import os
from models import (
    device as device_table,
    link as link_table
)

from flask import Flask
from flask import render_template, redirect, url_for, request, send_file
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from random import randint

import pandas as pd

from werkzeug.utils import secure_filename

def get_random_path(ext):
    """Generates random number with txt extention"""
    path = str(randint(0, 100000)) + "." + ext
    return path

def google(query):
    """Searches the query in Google
    Requires "Googler" command-line tool
    Returns list of URLS
    """
    stream = os.popen('googler ' + query + ' --np -C | grep http')
    output = stream.read()
    lst = output.split('\n')
    lst = list(filter(None, [s.strip() for s in lst]))
    return lst

def fetch(link, file_name):
    """Fetches the page by URL, renders it and
    outputs as text file in the current dir
    Requires "fetch.sh" bash script
    Returns a string with the output file name
    """
    dat = '"{0}"'.format(link)
    cmd = f"bash fetch.sh {file_name} {dat}"
    os.system(cmd)
    return file_name

def process_excell(path_1, path_2):
    """Reads the spreadsheet (path_1),
    processes it and outputs the result (path_2)
    Requires openpyxl
    """
    data_frame = pd.read_excel(path_1, engine='openpyxl')
    file_path = get_random_path("txt")
    for i, row in data_frame.iterrows():
        links = google(str(row['Product']) + ' MTBF')
        fnd = dict()
        for link in links:
            fetch(link, file_path)
            fnd[link] = yargy_parser(file_path)
            os.remove(file_path)
        res = finding_num(fnd)
        for param in res.keys():
            if param not in data_frame.columns:
                data_frame[param] = None
            data_frame[param][i] = res[param]
    data_frame.to_excel(path_2)


app = Flask(__name__, static_url_path='/static', static_folder='static')

class ExcellForm(FlaskForm):
    """A simple class for the form used by the uploader"""
    excell = FileField(validators=[FileRequired()])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page is used to retrieve the xls file from user"""
    form = ExcellForm(csrf_enabled=False)
    if form.validate_on_submit():
        f = form.excell.data
        #filename = secure_filename(f.filename)
        filename = get_random_path("xlsx")
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
            os.makedirs(app.instance_path + '/excells')
        path = os.path.join(
            app.instance_path, 'excells', filename
        )
        f.save(path)
        return redirect(url_for('result', filename=filename))

    return render_template('upload.html', form=form)


@app.route("/search", methods=['GET', 'POST'])
def search_page():
    """Result page for the manual search entered by user on index page"""
    query = request.args.get('query')
    
    device_query = select(
        device_table.c, device_table
    ).where(device_table.c.query == query)
    query_result = engine.execute(
        device_query
    ).fetchone()
    if query_result:
        return dict(query_result)

    return search_by_query(query)


def search_by_query(query: str) -> str:
    links = google(query + ' mtbf')
    fnd = dict()
    file_path = get_random_path("txt")
    for link in links:
        fetch(link, file_path)
        fnd[link] = yargy_parser(file_path)
        os.remove(file_path)
    res = finding_num(fnd)
    res['query'] = query

    # patch column names
    
    for k, v in res.copy().items():
        new_k  = '_'.join(k.lower().split())
        res[new_k] = res.pop(k)
    links = res.pop('links', [])
    device_id = engine.execute(
        insert(device_table, values=res).\
        returning(device_table.c.id)
    ).fetchone()[0]

    for link in links:
        engine.execute(
            insert(link_table, values={
                'link': link,
                'device_id': device_id
            })
        )
    return res


@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/result')
def result():
    """Returns the final xls to the user"""
    filename = request.args['filename']  # counterpart for url_for()
    fn = secure_filename(filename)
    path = os.path.join(
        app.instance_path, 'excells', fn
        )
    path_res = os.path.join(
        app.instance_path, 'excells', 'res_' + fn
        )
    process_excell(path, path_res)
    return send_file(path_res, as_attachment=True)


if __name__ == '__main__':
    engine = create_engine(
        'postgresql://postgres:docker@postgres:5432',
        echo = True
    )
    app.run(debug=True, host='0.0.0.0')
