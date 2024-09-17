"""uploader.py

This the python file which runs the flask server for the admin portal for the plan search tool.
It handles all the pages of the admin website i.e. 'upload', 'delete' and 'reindex'.

A user with appropriate rights (admin/superadmin) can upload, delete and re-index the database using
this portal.

The file contains the following functions:
    * home
    * do_admin_login
    * delete_page_update
    * upload_page_update
    * reindex_data
    * delete_file
    * upload_file1

"""

from __future__ import print_function

import shutil, os, sys, subprocess, bcrypt, es
import fitz, pytesseract, requests, cv2, textract
import subprocess, ghostscript, PyPDF2, json, re

from flask import Flask, request, render_template, redirect, flash, session, abort, url_for,Markup, jsonify
from flask_simple_geoip import SimpleGeoIP
from flask_mail import Mail, Message
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from PyPDF2 import PdfFileMerger, PdfFileReader
from werkzeug.utils import secure_filename
from datetime import datetime
from decouple import config
import smtplib


app = Flask(__name__)  # create flask object
mail= Mail(app)  # create mail object
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # to avoid storing cache
app.config["GEOIPIFY_API_KEY"] = "at_8RFyAJbk6JHFY9eJCUEuHOFEPMEjG"  # ip address finder API key
simple_geoip = SimpleGeoIP(app)  # ip address finder object

gauth = GoogleAuth()  # initiate google drive authentication
gauth.LoadCredentialsFile("mycreds.txt")  # load api credential details
drive = GoogleDrive(gauth)  # create drive object

fileg=open("drivep.txt","r")
gpp=fileg.readline()
fileg.close()
app.config['MAIL_SERVER']='smtp.gmail.com'  # use gmail server
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'generalplanserver@gmail.com'  
app.config['MAIL_PASSWORD'] = gpp  # set sender password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)  # build object again

# 0 means normal admin and 1 means superuser
userType = 0

blockip = {  # dictionary with list of ips to block
  "": 0,
}

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", endpoint = "/admin")

@app.route('/admin')
def home():
    """This function renders and controls login screen

    Returns:
        str: webpages
    """
    global userType
    del_list=""  # list of files in delete section
    for filename in sorted(os.listdir("static/data/places")):
        if filename.endswith(".txt"):
            filename=filename.replace(".txt","")
            del_list += '<option value="'+filename+'">'+filename+'</option>'  # add each file name in selection list
    del_list=Markup(del_list)  # mark the html script as safe object
    if not session.get('logged_in'):  # if not logged in, return login page
        return render_template('login.html')
    else:
        session['logged_in'] = False
        return render_template('upload_index.html',del_list=del_list, userType = userType)  # if logged in, update file list


@app.route('/admin', methods=['POST'])
def do_admin_login():  # function to collect username & password
    global blockip, userType
    if str(request.remote_addr)+"t" in blockip:  # check if the ip has exceeded the 10 try mark
        if (datetime.now()-blockip[str(request.remote_addr)+"t"]).total_seconds() <1800:
            cal=(1800-(datetime.now()-blockip[str(request.remote_addr)+"t"]).total_seconds())/60
            flash("Try again after "+str(int(cal))+" minutes")
        else:
            flash("Try again ")
            del blockip[str(request.remote_addr)+"t"]
    else:
        # import pdb; pdb.set_trace()
        userID = config('userID',default='')
        password = config('passw',default='')        
        superUserID = config('superUserID',default='')
        superUserPassword = config('superUserPassw',default='')

        pwHashed = password.encode('utf-8')
        superPwHashed = superUserPassword.encode('utf-8')
        pwd=request.form['password'].encode('utf-8')  # store password and encode to UTF-8
        if (bcrypt.checkpw(pwd, pwHashed) and request.form['username'] == userID) or (bcrypt.checkpw(pwd, superPwHashed) and request.form['username'] == superUserID):  # check username and password
            if str(request.remote_addr) in blockip:
                del blockip[str(request.remote_addr)]
            session['logged_in'] = True

            if request.form['username'] == userID:
                userType = 0
            else:
                userType = 1
        else:
            if str(request.remote_addr) in blockip:

                blockip[str(request.remote_addr)]+=1
                if blockip[str(request.remote_addr)]>10:  # check if ip address has exceeded 10 incorrect attempts
                        # send email for download notification
                        msg = Message('Excessive log in attempts', sender = 'generalplanserver@gmail.com', recipients = ['ckbrinkley@ucdavis.edu'])
                        geoip_data = simple_geoip.get_geoip_data()
                        ip=str(geoip_data['ip'])
                        co=str(geoip_data['location']['country'])
                        rg=str(geoip_data['location']['region'])
                        brow=request.user_agent.platform+" "+request.user_agent.browser
                        msg.body = "Dear Admin,\n\nThere have been excessive log in attempts on Uploader site. The details of the client are as follows:\n\nIP:"+ip+"\nCountry:"+co+"\nRegion:"+rg+"\nBrowser:"+brow+"\n\nGeneral Plan Server."
                        mail.send(msg)

                        flash('Excessive incorrect attempts, Try again after 30 minutes')

                        del blockip[str(request.remote_addr)]
                        blockip[str(request.remote_addr)+"t"]=datetime.now()
                else:
                    flash('Incorrect Username/Password, please try again')  # if ID doesnt match username & password
            else:
                blockip[str(request.remote_addr)]=0
                flash('Incorrect Username/Password, please try again')
    return home()


@app.route('/admin/delpg')
def delete_page_update():  # to update page list
    session['logged_in'] = True
    return redirect(url_for('home'))


@app.route('/admin/upload_confirm')
def upload_page_update():
    session['logged_in'] = True
    return redirect(url_for('home'))


@app.route('/admin/reindex')
def reindex_data():  # to update page list
    session['logged_in'] = True
    es.index_everything()
    
    ###### Updating the stats.json ######
    stats_dict = open('static/data/city_plans_files/stats.json')
    stats_data = json.load(stats_dict)
    stats_data["last_updated"] = datetime.now().strftime("%B %d, %Y")
    
    # Update the stats.json with new values
    stats_json_object = json.dumps(stats_data, indent=4)
    with open('static/data/city_plans_files/stats.json', "w") as outfile:
        outfile.write(stats_json_object)

    msg = "Files re-indexed Successfully!"
    return render_template('upload_reindex_done.html', msg=msg) 


@app.route('/admin/delete', methods = ['POST'])
def delete_file():  # function to delete file from list
    del_req=request.form['deleter']  # access delete button argument
    del_req=del_req+".pdf"
    rempdf = os.path.join("static/data/places", del_req)
    rempdftemp=rempdf.replace("places","temp")
    remtxt= rempdf.replace(".pdf",".txt")

    completeName = rempdf
    ###### Updating the stats.json ######
    stats_dict = open('static/data/city_plans_files/stats.json')
    stats_data = json.load(stats_dict)

    # Update the number of pdf pages
    print("Number of pages before:", stats_data["total_pages"])
    new_pdf_file = open(completeName, 'rb')
    read_pdf = PyPDF2.PdfFileReader(new_pdf_file)
    stats_data["total_pages"] -= read_pdf.numPages
    print("Number of pages after:", stats_data["total_pages"])

    # Update the number of words
    print("Number of words before:", stats_data["total_words"])
    text = textract.process(completeName).decode('utf-8')
    words = re.findall(r"[^\W_]+", text, re.MULTILINE)
    stats_data["total_words"] -= len(words)
    print("Number of words after:", stats_data["total_words"])

    # Update the file count
    print("Number of files before:", stats_data["file_count"])
    stats_data["file_count"] -= 1
    print("Number of files after:", stats_data["file_count"])

    # TODO: Update missing cities and counties (FUTURE WORK)

    # Update the stats.json with new values
    stats_json_object = json.dumps(stats_data, indent=4)
    with open('static/data/city_plans_files/stats.json', "w") as outfile:
        outfile.write(stats_json_object)
    #####################################

    try:
        os.remove(remtxt)  # remove text file followed by pdf
    except:
        print("not found")
    try:
        os.remove(rempdf)  # remove text file followed by pdf
    except:
        print("not found")
    try:
        os.remove(rempdftemp)  # remove text file followed by pdf
    except:
        print("not found")

    ########### GOOGLE DRIVE AUTH STUFF ##################
    # drive = GoogleDrive(gauth)  # rebuild the drive object
    # top_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()  # generate list of files in drive
    # for fileu in top_list:
    #     if fileu['originalFilename'] == del_req:  # delete file matching the delete request from drive
    #         fileu.Delete()


    return redirect(url_for('delete_page_update'))


@app.route('/admin/upload', methods = ['GET', 'POST'])  # route to upload form in upload_index html in for getting files and posting to the server
def upload_file1():  # function to upload file
    global userType
    completeName=""
    location_name=""
    up=""
    if request.method == 'POST':  # when upload button is clicked
        if userType == 0:
            gauth = GoogleAuth()

            # Try to load saved client credentials
            gauth.LoadCredentialsFile("mycreds.txt")
              
            if gauth.credentials is None:
                # Authenticate if they're not there
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                # Refresh them if expired
                gauth.Refresh()
            else:
                # Initialize the saved creds
                gauth.Authorize()
                
            # Save the current credentials to a file
            gauth.SaveCredentialsFile("mycreds.txt")

            drive = GoogleDrive(gauth)

            # Issues needed to kept in mind:
            #     The authentication has to be done for the first time
            #     Explore the settings.yaml option
            #     What if the token expires, how to manage that?
            #     Need to check all fields are filled and check email validity

            files = request.files.getlist("file")  # get list of files uploaded in form
            for file in files:  # open place pdf file
                print(file.filename)
                location_name=""
                if request.form['type'] == "City":
                    location_name=request.form['City']
                else:
                    location_name=request.form['county']
            
            # generate filename with select form data
            location_name.replace(" ", "-")
            file.filename=request.form['state']+"_"+request.form['type']+"-"+location_name+"_"+request.form['year']+".pdf"
            print(file.filename)
            tempLocation = os.path.join("static/data/temp",file.filename)
            file.save(tempLocation)
            print("File uploaded to temp location")

            # Adding the file to google drive
            upload_file_list = [tempLocation]
            for upload_file in upload_file_list:
                gfile = drive.CreateFile({'parents': [{'title': file.filename, 'id': '1o-BiWU94SApuxZY5serVBDBn5pA_7ZYz'}]}) # id of the folder from URL
                # Read file and set it as the content of this instance.
                gfile['title'] = file.filename
                gfile.SetContentFile(upload_file)
                gfile.Upload() # Upload the file.
                gfile = None
                print("File uploaded to google drive")

            # Remove the uploaded file from temp
            os.remove(tempLocation)
            print("File deleted from temp location")

            gmail_user = config('gmailUserID',default='')
            gmail_password = config('gmailUserPassw',default='')

            sent_from = gmail_user
            to = [request.form['email'], gmail_user]
            subject = 'File uploaded for verification'
            body = 'Dear User,\nYour file {} has been uploaded to drive for verification.'.format(file.filename)

            email_text = 'To: {}\nSubject: {}\n\n{}'.format(", ".join(to), subject, body)

            try:
                smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                smtp_server.ehlo()
                smtp_server.login(gmail_user, gmail_password)
                smtp_server.sendmail(sent_from, to, email_text)
                smtp_server.close()
                print ("Email sent successfully!")
            except Exception as ex:
                print ("Something went wrong….",ex)


            up="Files uploaded for verification!"
            print("This file is uploaded to drive:",tempLocation)

        else:
            files = request.files.getlist("file")  # get list of files uploaded in form
            for file in files:  # open place pdf file
                print(file.filename)
                location_name=""
                if request.form['type'] == "City":
                    location_name=request.form['City']
                else:
                    location_name=request.form['county']
                
                # generate filename with select form data
                location_name.replace(" ", "-")
                file.filename=request.form['state']+"_"+request.form['type']+"-"+location_name+"_"+request.form['year']+".pdf"
                print(file.filename)

                completeName = os.path.join("static/data/places",file.filename)

                print(completeName)
                # temporary copy file in case compression is not possible
                tempname=os.path.join("static/data/temp",secure_filename(file.filename)) 
                print("hello.",tempname)
                file.save(completeName)  # save file to server
                arg1= '-sOutputFile='+ tempname  # path for output file after compression to reduce pdf size

                # path to ghostscript in user's OS has to be changed
                p = subprocess.Popen(['/usr/bin/gs',
                                      '-sDEVICE=pdfwrite','-dCompatibilityLevel=1.4',
                                      '-dPDFSETTINGS=/screen','-dNOPAUSE', '-dBATCH',  '-dQUIET',
                                      str(arg1),completeName ], stdout=subprocess.PIPE)  # function to compress pdf
                try:
                    out, err = p.communicate(timeout=1800)  # try compression for 1800 secs max
                except subprocess.TimeoutExpired:
                    p.kill()  # kill the process since a timeout was triggered
                    out, error = p.communicate()  # capture both standard output and standard error
                else:
                    pass

                try:
                    fh= open(tempname, "rb")
                    check=PyPDF2.PdfFileReader(fh)  # check if pdf is valid file
                    fh.close()
                except:
                    fh= open(tempname, "rb")
                    print("invalid PDF file")
                    fh.close()
                    os.remove(tempname)  # remove temp file if compressed pdf is corrupt and causes exception
                else:
                    pass
                    os.remove(completeName)
                    # try:
                    shutil.move(tempname,"static/data/places")  # move compressed tempfile to places directory is compressed file is valid
                    # except OSError as error:
                    # print(error) # need to trigger a popup in the browser window
                fname =completeName
                fnamecpy=fname
                doc = fitz.open(fname)  # open pdf file object
                length=len(doc)  # find no. of pages
                imornot=0  # flag variable to check if pdf contains scanned data or text
                for page in doc:
                    if not page.getText():  # check if pdf contains scanned data or text
                        imornot=imornot+1

                text_file_name = fname + ".txt"
                if imornot > int(length/2):  # if more than half pages of pdf are scanned convert to text pdf through OCR
                    fname=fname.replace('.pdf', '')
                    text_file_name = fname + ".txt"
                    textfile = open(text_file_name, "a")  # create text file with place name
                    for page in doc:
                        pix = page.getPixmap(alpha = False)  # generate image file from page
                        pixn=os.path.join("static/data/places","page-%i.png" % page.number)
                        pix.writePNG(pixn)  # save page image as png
                        pdfn=os.path.join("static/data/places","page-"+str(page.number)+".pdf")
                        with open(pdfn, 'w+b') as f:
                            # ********* UPDATED OCR CODE *********** # 
                            # Grayscale, Gaussian blur, Otsu's threshold
                            image = cv2.imread(pixn)
                            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                            blur = cv2.GaussianBlur(gray, (3,3), 0)
                            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                            # Morph open to remove noise and invert image
                            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
                            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
                            invert = 255 - opening
                            # Perform text extraction
                            text = pytesseract.image_to_string(invert, lang='eng', config='--psm 6')
                            # *******************
                            textfile.write(text)  # write text from the image to text file
                            pdf = pytesseract.image_to_pdf_or_hocr(pixn, extension='pdf')  # convert image to pdf
                            f.write(pdf)  # create pdf for the page
                            os.remove(pixn)  # remove the image after pdf creation
                        f.close()
                    textfile.close()

                    mergedObject = PdfFileMerger()  # create file merger object

                    # merge all page pdfs into a single pdf for the particular place
                    for fileNumber in range(page.number+1):
                        pdfn=os.path.join("static/data/places",("page-"+str(fileNumber)+".pdf"))
                        mergedObject.append(PdfFileReader(pdfn, 'rb'))  # append page to place pdf
                        os.remove(pdfn)  # remove appended page pdf from server

                    mergedObject.write(fnamecpy)  # save the complete place pdf to single file in server

                    mergedObject.close()


                else:  # if the pdf contains less than half scanned pages
                    imornot=0
                    fname=fname.replace('.pdf', '')
                    textfile = open(fname + ".txt", "wb")  # create text document to store text data
                    for page in doc:
                            text = page.getText().encode("utf8")  # get text from pdf page
                            textfile.write(text)  # write text to text file for the place
                            textfile.write(bytes((12,)))
                    textfile.close()

                doc.close()

                up="Files Uploaded Successfully!"
            print("This file is uploaded:",completeName)

            ###### Updating the stats.json ######
            stats_dict = open('static/data/city_plans_files/stats.json')
            stats_data = json.load(stats_dict)

            # Update the number of pdf pages
            print("Number of pages before:", stats_data["total_pages"])
            new_pdf_file = open(completeName, 'rb')
            read_pdf = PyPDF2.PdfFileReader(new_pdf_file)
            stats_data["total_pages"] += read_pdf.numPages
            print("Number of pages after:", stats_data["total_pages"])

            # Update the number of words
            print("Number of words before:", stats_data["total_words"])
            text = textract.process(completeName).decode('utf-8')
            words = re.findall(r"[^\W_]+", text, re.MULTILINE)
            stats_data["total_words"] += len(words)
            print("Number of words after:", stats_data["total_words"])

            # Update the file count
            print("Number of files before:", stats_data["file_count"])
            stats_data["file_count"] += 1
            print("Number of files after:", stats_data["file_count"])

            # TODO: Update missing cities and counties (FUTURE WORK)

            # Update the stats.json with new values
            stats_json_object = json.dumps(stats_data, indent=4)
            with open('static/data/city_plans_files/stats.json', "w") as outfile:
                outfile.write(stats_json_object)
            #####################################

    return render_template('upload_confirm.html',up=up)  # render upload confirmation message page


if __name__ == "__main__":  # run app on local host at port 5001 in debug mode
    app.secret_key = os.urandom(12)  # random key for log in authentication
    app.run(host="0.0.0.0", port=5002, debug=False)
