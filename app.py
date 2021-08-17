from flask import Flask, render_template, flash, request, redirect, url_for, send_file
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
    for folder in ['uploads','downloads']:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

@app.route("/", methods=['GET', 'POST'])
def upload_file():
    filefound = False
    delete_files()
    if request.method == 'POST':
        allkeys = [key for (key, value) in request.form.items()]
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return render_template('index.html')
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return render_template('index.html')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filefound = True
    if filefound:
        # now the data manipulation begins...
        df = pd.read_excel('uploads/'+filename, engine='openpyxl')
        foodlist = df.values.tolist()
        foodlist = [item for item in foodlist if (pd.isna(item[0]) == False)]
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
        # setting up set dict
        # convert corr_dict to corr_set_dict
        setdict = dict()
        newdict = dict()
        for key in corrdict:
            newdict[key] = []
            setdict[key] = list(set([item for (item, price) in corrdict[key]]))
            for new_item in setdict[key]:
                item_total = 0
                for orig_item, price in corrdict[key]:
                    if new_item == orig_item:
                        item_total += float(price)
                newdict[key].append((new_item, item_total))
        exceldict = dict()
        for key in newdict:
            filler_lst = []
            for i, p in newdict[key]:
                filler_lst.append((p,i))
            excel_lst = []
            for p,i  in sorted(filler_lst, reverse=True):
                excel_lst.append((i,p))
            exceldict[key] = excel_lst
        # write to Excel
        writer = pd.ExcelWriter('downloads/categorized_output.xlsx')
        for key in list(exceldict.keys()):
            currentcatlist = exceldict[key]
            currentdf = pd.DataFrame.from_records(sorted(currentcatlist, key=lambda item: item[1], reverse=True))
            currentdf = currentdf.rename(columns={0: 'Item Name', 1: 'Dollars'})
            newkey = ''
            for char in key:
                if char in ['[', ']', ':', '*', '?', '/', '\\']:
                    newkey = newkey + " "
                else:
                    newkey = newkey + char
            if len(newkey) > 31:
                newkey = newkey[:31]
            # Save df to one Excel sheet 
            currentdf.to_excel(writer, newkey)
        writer.save()
        if allkeys == ['getcats']:
            return send_file('downloads/categorized_output.xlsx',
                        mimetype='text/xlsx',
                        attachment_filename='Cool_Food_Categorized_Output.xlsx',
                        as_attachment=True)
        elif allkeys == ['getprices']:
            # get total prices
            totalpricedict = {}
            for key in corrdict:
                totalpricedict[key] = 0
                for item, price in corrdict[key]:
                    totalpricedict[key] += price
            writer = pd.ExcelWriter('downloads/Cool_Food_Price_Totals.xlsx')
            datapoints = []
            for key in list(totalpricedict.keys()):
                datapoint = list((key, totalpricedict[key]))
                datapoints.append(datapoint)
            currentdf = pd.DataFrame.from_records(datapoints)
            currentdf = currentdf.rename(columns={0: 'CFP Category', 1: 'Total Dollars Purchased'})
            currentdf.to_excel(writer)
            writer.save()
            return send_file('downloads/Cool_Food_Price_Totals.xlsx',
                        mimetype='text/xlsx',
                        attachment_filename='Cool_Food_Price_Totals.xlsx',
                        as_attachment=True)
        else:
            # find items which go unused (new)
            set_of_items = set()
            for cat in corrdict:
                for item in corrdict[cat]:
                    item_name = item[0]
                    set_of_items.add(item_name)
            not_used = set()
            for item in foodlist:
                item_name = item[0]
                if item_name not in set_of_items:
                    not_used.add(tuple(item))
            writer = pd.ExcelWriter('downloads/Uncategorized_Items.xlsx')
            currentdf = pd.DataFrame(sorted(list(not_used), key=lambda item: item[1], reverse=False))
            currentdf = currentdf.rename(columns={0: 'Item (uncategorized)', 1: 'Dollars'})
            # Save df to one Excel sheet 
            currentdf.to_excel(writer)
            writer.save()
            return send_file('downloads/Uncategorized_Items.xlsx',
                        mimetype='text/xlsx',
                        attachment_filename='Uncategorized_Items.xlsx',
                        as_attachment=True)

    return render_template('index.html')

if __name__ == '__main__':
   app.run()