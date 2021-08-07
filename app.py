from flask import Flask, render_template, flash, request, redirect, url_for
import os
import pandas as pd
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx','xls'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def delete_files():
    for f in os.listdir('uploads'):
        os.remove(os.path.join('uploads', f))

@app.route("/", methods=['GET', 'POST'])
def upload_file():
    filefound = False
    if request.method == 'POST':
        delete_files()
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return render_template('index.html',upload='has failed!')
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return render_template('index.html',upload='has failed!')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filefound = True
    if filefound:
        # now the data manipulation begins...
        df = pd.read_excel('uploads/'+filename, engine='openpyxl')
        foodlist = df.values.tolist()
        # categorization
        textlist = []
        keyworddict = {}

        # Initialize key values from cat to keyword document
        with open('keywords.txt', 'r') as file:
            for text in file:
                textlist.append(text)
        # Make dictionary with cat and keywords
        for row in textlist:
            for item in row.split(','):
                if item.startswith('CATEGORY'):
                    catname = item[10:]
                    keyworddict[catname] = []
                elif item == '\n' or item == ' ' or item == None:
                    continue
                else:
                    keyworddict[catname].append(item.strip())
        # now the antikeywords
        nottextlist = []
        notkeyworddict = {}
        with open('notkeywords.txt', 'r') as file:
            for text in file:
                nottextlist.append(text)
        # Make dictionary with cat and keywords
        for row in nottextlist:
            for item in row.split(','):
                if item.startswith('CATEGORY'):
                    catname = item[10:]
                    notkeyworddict[catname] = []
                elif item.strip() in ['\n', '\t', ' ' , '', None]:
                    continue
                else:
                    notkeyworddict[catname].append(item.strip())
        # separate all data points by keywords into correlation dictionary
        corrdict = {}
        for cat in keyworddict.keys():
            corrdict[cat] = []
            for food in foodlist:
                for entry in keyworddict[cat]:
                    if entry.lower() in food[0].lower():
                        corrdict[cat].append(food)

        # clean up time (remove words caught by nonkeywords)
        for cfpcat in corrdict.keys():
            correctlist = []
            for food in corrdict[cfpcat]:
                bad = False
                for word in notkeyworddict[cfpcat]:
                    if word.lower() in food[0].lower():
                        bad = True
                if bad == False:
                    correctlist.append(food)
            corrdict[cfpcat] = correctlist
        # correlation dictionary complete
        for item in corrdict['Eggs']:
            print(item)
        return render_template('index.html',upload='of '+filename+' is a success!')

    return render_template('index.html',upload='is not complete yet.')

if __name__ == '__main__':
   app.run()