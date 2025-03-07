"""dbStats.py

Aim of this file is to just get information related to all the files in our db.
Currently we get info of each file:
    Name, Year, Pages, Type, State

This program will return a csv of this data.

"""

import os
import PyPDF2
import pandas as pd
from datetime import datetime

# places folder location
filesLocation = "static/data/places"

results = []

for fileName in os.listdir(filesLocation):
    if fileName.lower().endswith(".pdf"):
        placeInfo1 = fileName.split("-")
        placeInfo2 = placeInfo1[0].split("_")
        placeInfo3 = placeInfo1[1].split("_")
        stateName = placeInfo2[0]
        placeType = placeInfo2[1]
        placeName = placeInfo3[0]
        try:
            planYear = placeInfo3[1][:-4]
        except:
            planYear = 0

        planInfo = {}
        planInfo["Name"] = placeName
        planInfo["Type"] = placeType
        planInfo["Year"] = planYear
        planInfo["State"] = stateName
        
        try:
            completeName = os.path.join(filesLocation, fileName)
            new_pdf_file = open(completeName, 'rb')
            read_pdf = PyPDF2.PdfFileReader(new_pdf_file)
            planInfo["Pages"] = read_pdf.numPages
        except:
            planInfo["Pages"] = 0

        results.append(planInfo)
        print("{} Done".format(placeName))

print(results)
today_date = datetime.today().strftime("%Y-%m-%d")
df = pd.DataFrame(results)
csv_filename = f"dbStats_{today_date}.csv"
df.to_csv(csv_filename, index=False, encoding="utf-8")