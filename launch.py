import os

from parser import yargy_parser
from parser import finding_num

from flask import Flask
from flask import render_template, redirect, url_for, request, send_file
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired

import pandas as pd

from werkzeug.utils import secure_filename

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

def fetch(link):
    """Fetches the page by URL, renders it and
    outputs as text file in the current dir
    Requires "fetch.sh" bash script
    Returns a string with the output file name
    """
    dat = '"{0}"'.format(link)
    cmd = "bash fetch.sh " + dat
    os.system(cmd)
    return "texts.txt"

def process_excell(path_1, path_2):
    """Reads the spreadsheet (path_1),
    processes it and outputs the result (path_2)
    Requires openpyxl
    """
    data_frame = pd.read_excel(path_1, engine='openpyxl')
    for i, row in data_frame.iterrows():
        links = google(row['Product'] + ' MTBF')
        fnd = dict()
        print(links)
        for link in links:
            path = fetch(link)
            fnd[link] = yargy_parser(path)
        print(fnd)
        res = finding_num(fnd)
        for param in res.keys():
            data_frame[param][i] = res[param]
    data_frame.to_excel(path_2)


app = Flask(__name__)             # create an app instance

class ExcellForm(FlaskForm):
    """A simple class for the form used by the uploader"""
    excell = FileField(validators=[FileRequired()])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page is used to retrieve the xls file from user"""
    form = ExcellForm(csrf_enabled=False)
    if form.validate_on_submit():
        f = form.excell.data
        filename = secure_filename(f.filename)
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
    links = google(query)
    path = fetch(links)
    fnd = yargy_parser(path)
    res = str(finding_num(fnd))
    return "Found for "+ query+": " + res

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

app.run(debug=True, host='0.0.0.0')                     # run the flask app
