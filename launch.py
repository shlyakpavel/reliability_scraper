import os
from random import randint
from threading import Thread

from parser import yargy_parser
from parser import finding_num

from flask import Flask
from flask import render_template, redirect, url_for, request, send_file
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired

import pandas as pd

from werkzeug.utils import secure_filename

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
    links = google(query + ' mtbf')
    fnd = dict()
    file_path = get_random_path("txt")
    for link in links:
        fetch(link, file_path)
        fnd[link] = yargy_parser(file_path)
        os.remove(file_path)
    res = str(finding_num(fnd))
    return "Found for "+ query+": " + res

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

app.run(debug=True, host='0.0.0.0')                     # run the flask app
