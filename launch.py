from flask import Flask           # import flask
from flask import render_template, redirect, url_for, session, request, send_file
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired

from parser import yargy_parser
from parser import finding_num

import pandas as pd

from werkzeug.utils import secure_filename

import os
def google(query):
    stream = os.popen('googler ' + query + ' --np -C | grep http')
    output = stream.read()
    lst = output.split('\n')
    lst = list(filter(None, [s.strip() for s in lst]))
    return lst

def fetch(links):
    data = str()
    cmd = "bash fetch.sh " + " ".join(links)
    os.system(cmd)
    return "texts.txt"

def process_excell(path_1, path_2):
    df = pd.read_excel(path_1, engine='openpyxl')
    for i, row in df.iterrows():
        links = google(row['Product'] + ' MTBF')
        path = fetch(links)
        fnd = yargy_parser(path)
        res = finding_num(fnd)
        df["MTBF"][i] = res["MTBF"]
        df["MTTR"][i] = res["MTTR"]
    df.to_excel(path_2)


app = Flask(__name__)             # create an app instance

class ExcellForm(FlaskForm):
    excell = FileField(validators=[FileRequired()])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
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
        #session['filename'] = filename
        return redirect(url_for('result', filename=filename))

    return render_template('upload.html', form=form)


@app.route("/search", methods=['GET', 'POST'])              # at the end point /<name>
def hello_name():              # call method hello_name
    query = request.args.get('query')
    links = google(query)
    path = fetch(links)
    fnd = yargy_parser(path)
    res = str(finding_num(fnd))
    return "Found for "+ query+": " + res

@app.route('/')              # at the end point /<name>
def index():              # call method hello_name
    return render_template('index.html')

@app.route('/result')              # at the end point /<name>
def result():              # call method hello_name
    filename = request.args['filename']  # counterpart for url_for()
    fn = secure_filename(filename)
    #messages = session['filename']
    path = os.path.join(
        app.instance_path, 'excells', fn
        )
    path_res = os.path.join(
        app.instance_path, 'excells', 'res_' + fn
        )
    prods = process_excell(path, path_res)
    return send_file(path_res, as_attachment=True)

app.run(debug=True,host='0.0.0.0')                     # run the flask app
