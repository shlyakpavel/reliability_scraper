import os
from random import randint
from threading import Thread

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

import pandas as pd

from werkzeug.utils import secure_filename


app = Flask(
    __name__,
    static_url_path='/static',
    static_folder='static'
)


THREADS = {}

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

    QUERY_COLUMN = 'Product'
    result_list = []
    for query in data_frame[QUERY_COLUMN]:
        if str(query) == 'nan':
          continue
        select_query = select(
            device_table.c,
            device_table
        ).where(
            device_table.c.query == query
        )
        query_result = engine.execute(select_query).fetchone()
        if query_result:
            result_dict = dict(query_result)
            links = [
                row[0] for row in 
                engine.execute(
                select([link_table.c.link], link_table).where(
                    link_table.c.device_id == result_dict['id'])
                ).fetchall()
            ]
            result_dict['links'] = links
            result_dict.pop('id', None)
            result_list.append(
                result_dict
            )
        else:
            result = search_by_query(query)
            result.pop('id', None)
            result_list.append(
                result
            )
    
    result_df = pd.DataFrame(result_list)
    result_df.columns = [
        ' '.join(col.split('_')).capitalize()
        for col in result_df.columns
    ]
    result_df = result_df.rename(columns={"Query": QUERY_COLUMN})

    result_df.to_excel(path_2)



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


def _patch_dict_keys(dict_):
    for k, v in dict_.copy().items():
        new_k  = '_'.join(k.lower().split())
        dict_[new_k] = dict_.pop(k)
    return dict_


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
    res = _patch_dict_keys(res)
    
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
    """Start processing and wait for the result on this page"""
    filename = request.args['filename']  # counterpart for url_for()
    secure_fn = secure_filename(filename)
    path = os.path.join(
        app.instance_path, 'excells', secure_fn
        )
    path_res = os.path.join(
        app.instance_path, 'excells', 'res_' + secure_fn
        )
    thread = Thread(target=process_excell, args=(path, path_res,))
    thread.daemon = True
    thread.start()
    THREADS[filename] = thread
    return render_template('result.html', status_url='/status?filename=' + filename,
                           download_url='/download?filename=' + filename,)

@app.route('/status')
def status():
    """Returns True is the thread is still running, False otherwise"""
    filename = request.args['filename']
    return str(THREADS[filename].isAlive())

@app.route('/download')
def download():
    """Return XLSX to user"""
    filename = request.args['filename']  # counterpart for url_for()
    secure_fn = secure_filename(filename)
    path_res = os.path.join(
        app.instance_path, 'excells', 'res_' + secure_fn
        )
    secure_fn = secure_filename(filename)
    return send_file(path_res, as_attachment=True)


if __name__ == '__main__':
    engine = create_engine(
        'postgresql://postgres:docker@postgres:5432',
        echo=True
    )
    app.run(debug=True, host='0.0.0.0')
