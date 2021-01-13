import os
from flask import Flask, request, render_template
from flask import flash, redirect, session, abort
from PyPDF2 import PdfFileMerger, PdfFileReader
import fitz
from werkzeug.utils import secure_filename
from flask_bootstrap import Bootstrap 
from flask import Markup
import pandas as pd
import requests
import shutil
from bokeh.resources import CDN
from bokeh.embed import components
from bokeh.plotting import figure
import geopandas as gpd
from bokeh.models import GeoJSONDataSource
import json
from bokeh.io import show, curdoc
from bokeh.models import LogColorMapper, ColumnDataSource, DataTable, DateFormatter, TableColumn, NumberFormatter, HTMLTemplateFormatter, Div
from bokeh.palettes import Viridis6 as palette
from bokeh.sampledata.unemployment import data as unemployment
from bokeh.sampledata.us_counties import data as counties
from bokeh.layouts import column, widgetbox, layout, row
import shapefile
from bokeh.models.callbacks import CustomJS
from bokeh.io import output_file, show
from bokeh.models import TextInput, Button
from bokeh.models.widgets import Panel, Tabs
from bokeh.io import show, output_file
import shapely.affinity

app = Flask(__name__)                                                                                                               #create flask object
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0                                                                                         #avoid storing cache
bootstrap = Bootstrap(app)                                                                                                          #create bootstrap object





@app.route('/')                                                                                                                     #declare flask page url
def my_form():                                                                                                                      #function for main index

    return render_template('index.html')                                                                                            #return index page



def getResults(wordinput):                                                                                                          
    
    countyPopFile = open('static/data/countyPopulations.csv')
    countyPops = {}
    for line in countyPopFile:
        parts = line.split(',')
        countyPops[parts[0]] = parts[1]
    countyPopFile.close()
    
    
    cityPopFile = open('static/data/cityPopulations.csv')
    cityPops = []
    for line in cityPopFile:
        parts = line.split(',')
        temp = cityPop()
        temp.name=parts[0]
        temp.type = parts[1]
        temp.county = parts[2]
        temp.population = parts[3]
        cityPops.append(temp)
    
    
    txtFilenames = []
    for filename in os.listdir("static/data/places"):
        if filename.endswith(".txt"):

            txtFilenames.append(filename)
    results = []
    query = wordinput
    word = query.split(",")
    wordcount = len(word)
    for fName in txtFilenames:
        isMatch = False
        file = open("static/data/places/" + fName, 'r',errors='ignore')
        
        
        with open("static/data/places/" + fName, 'r',errors='ignore') as file:
            data = file.read().replace('\n', '')
        data = data.lower()
        occurences = []
        for w in word:
            num = data.count(w)
            occurences.append(num)
            if isMatch or num > 0:
                isMatch = True
        if isMatch:
            tempResult = result(cityFile = fName, wordcount=wordcount)
            tempResult.type = fName.split('-')[0].split('_')[1]
            parts = fName.split('-')[1:]
            parts[-1] = parts[-1].split('.')[0]
            year = parts[-1].split('_')[1]
            parts[-1] = parts[-1].split('_')[0]
            name = ""
            for part in parts:
                name += part + " "
            name = name[:-1]
            tempResult.cityName = name
            tempResult.year = year
            tempResult.occurences = occurences
            if tempResult.type == 'county':
                tempResult.population = int(countyPops[tempResult.cityName])
            else:
                cityPopVal = [pop for pop in cityPops if pop.name == tempResult.cityName]
                if len(cityPopVal) != 0:

                    tempResult.population = int(cityPopVal[0].population)
                    tempResult.cityType = cityPopVal[0].type
                    tempResult.county = cityPopVal[0].county
            results.append(tempResult)
    if len(results) > 0:
        for res in results:
            for item in res.occurences:
                item = float(item)
        results.sort(key=lambda x: x.totalOccurences, reverse=True)
    return results, cityPops, countyPops  

class cityPop:
    
    def __init__(self, name="na"):
        
        self.county = "na"
        self.population = "na"
        self.name = "na"
        self.type = "na"
    
class result:
    
    def __init__(self, cityFile="", wordcount=0):
        
        self.cityFile = cityFile
        self.occurences = [0] * wordcount
        self.totalOccurences = 0
        self.cityName = ""
        self.type = "city"
        self.year = "na"
        self.county = "na"
        self.population = "0"
        self.cityType = "na"


        
@app.route('/', methods=['POST'])                                                                                                   #connect search form to html page
def index_search_box():                                                                                                             #function for accepting search input
    
    wordcount=1                                                                                                                     #initialize no. of phrase inputs
    flag=0
    wordinput=" "                                                                                                                   #initialize string input for search
    wordinput=request.form['u']                                                                                                     #set name for search form
    wordinput=wordinput.lower()                                                                                                     #convert input string to lowercase for non case sensitive search
    wordinput_copy=wordinput                                                                                                        #copy of input string
    wordlist=""                                                                                                                     #list of phrase input in single string
    phrase_split = wordinput_copy.split(",")                                                                                        #split input phrase into multiple words at every comma
    wordcount=len(phrase_split)                                                                                                     #count no. of phrases in input
    for x in range(wordcount):
        if wordcount ==1:
            wordlist= phrase_split[0]
            break
        wordlist += phrase_split[x]+','                                                                                             #add commas after every phrase
    wordlist= wordlist.strip(',')                                                                                                   #remove commas from end and beginning of string input
    results, cityPops, countyPops = getResults(wordinput)
    cityResults = []
    countyResults = []
    uniqueCities = 0
    uniqueCounties = 0
    for res in results:
        res.cityFile = res.cityFile.split('.')[0]+'.pdf'
        res.year = '<p hidden>'+res.year+'</p> <a href="outp/'+res.cityFile+'/'+wordlist+'" target="_blank">'+res.year+"</a>"
        if res.type == "county":
            countyResults.append(res)
        else:
            cityResults.append(res)
    global txtFilenames 
    
    query = wordinput
    word = query.split(",")
    #results = getResults(wordinput)
    if len(results) < 1:
        return render_template('noresult.html')
    
    cities = gpd.read_file("static/data/ca-places-boundaries/cities.shp")[['NAME','NAMELSAD', 'geometry']]
    cities.columns = ['name', 'color', 'geometry']
    cities.color = "#d47500"
    cities['line_color'] = '#dedede'
    numCities = len(cities.index)
    
    cityResultsName = [res.cityName for res in results]
    cityNames = cities['name'].to_list()
    for ind in cities.index:
        val = cityNames[ind]
        if val not in cityResultsName:
            cities.at[ind, 'color']='white'
    
    counties = gpd.read_file("static/data/CA_Counties/CA_Counties_TIGER2016.shp")[['NAME', 'NAMELSAD', 'geometry']]
    counties.columns = ['color', 'name', 'geometry']
    counties.color = "#00a4a6"
    counties['line_color'] = '#b3b3b3'
    numCounties = len(counties.index)
    
    for ind in counties.index:
        parts = counties['name'][ind].split(' ')[0:-1]
        val = ""
        if len(parts) == 1:
            val = parts[0]
        else:
            for part in parts:
                val += part + ' '
            val = val[0:-1]
        #print(val, flush=True)
        flag = False
        for res in results:
            if res.type == 'county':
                if val == res.cityName:
                    flag = True
        if not flag:
            counties.at[ind, 'color'] = 'white'
    
    combined = counties.append(cities)
    mergedJson = json.loads(combined.to_json())
    jsonCombined = json.dumps(mergedJson)
    geosource = GeoJSONDataSource(geojson = jsonCombined)
    
    TOOLS = ["hover", "pan", "wheel_zoom", "save"]
    p2 = figure(
        x_axis_location=None, y_axis_location=None,
        x_axis_type="mercator", y_axis_type="mercator",
        tools=TOOLS,
        tooltips=[("Name", "@name")]
        )
    p2.grid.grid_line_color = None
    p2.hover.point_policy = "follow_mouse"
    maxCountyPop = 1
    for county in countyResults:
        if county.population > maxCountyPop:
            maxCountyPop = county.population
    cartCounties = counties
    for ind in cartCounties.index:
        names = counties['name'][ind].split(' ')[0:-1]
        name = names[0]
        if len(names) > 1:
            for n in names[1:]:
                name += ' ' + n
        pop = float(countyPops[name])
        geo = cartCounties['geometry'][ind]
        if maxCountyPop == 1:
            scale = 1
        else:
            scale = (pop/maxCountyPop )**(1/2)
        cartCounties['geometry'][ind] = shapely.affinity.scale(geo, scale, scale)

    
    maxCityPop = 1
    for city in cityResults:
        if float(city.population) > float(maxCityPop):
            maxCityPop = city.population
    cartCities = cities
    for ind in cartCities.index:
        name = cities['name'][ind]
        pop = [r.population for r in cityPops if r.name == name]
        if len(pop) > 0:
            pop = float(pop[0])
        else:
            pop = 0.0
        geo = cartCities['geometry'][ind]
        if maxCityPop == 1:
            scale = 1
        else:
            scale = (pop/maxCityPop)**(1/2)
        cartCities['geometry'][ind] = shapely.affinity.scale(geo,scale,scale)
     
    combined = cartCounties.append(cartCities)
    countyJson = json.loads(combined.to_json())
    jsonCounty=json.dumps(countyJson)
    p2GeoSource = GeoJSONDataSource(geojson=jsonCounty)
    p2.patches('xs','ys',source=p2GeoSource,fill_color='color', line_color='line_color')   
    
    size = 850
    TOOLS = ["hover", "pan", "wheel_zoom", "save"]
    p = figure( 
        x_axis_location=None, y_axis_location=None,
        tools=TOOLS,
        tooltips=[("Name", "@name")])
    p.grid.grid_line_color = None
    p.hover.point_policy = "follow_mouse"
    p.patches('xs','ys', source = geosource, fill_color='color', line_color='line_color')
    

    cityData = dict(
        names=[res.cityName for res in cityResults],
        years=[res.year for res in cityResults],
        types=[res.cityType for res in cityResults],
        fNames=[res.cityFile for res in cityResults],
        populations = [res.population for res in cityResults],
        counties = [res.county for res in cityResults],
        )
    countyData = dict(
        names=[res.cityName for res in countyResults],
        years=[res.year for res in countyResults],
        types=[res.type for res in countyResults],
        fNames=[res.cityFile for res in countyResults],
        populations=[res.population for res in countyResults],
        )
    
    uniqueCities = len(set(cityData["names"]))
    uniqueCounties = len(set(countyData["names"]))
    occurences=[res.totalOccurences for res in results],
    numOccurences = len(results[0].occurences)
    
    for i,w in enumerate(phrase_split):
        cityOccurences = [cityres.occurences[i] for cityres in cityResults]
        cityData[w] = cityOccurences
        countyOccurences = [countyres.occurences[i] for countyres in countyResults]
        countyData[w] = countyOccurences
    
    citySource = ColumnDataSource(cityData)
    
    columns = [
            TableColumn(field="names", title="Name"),
            TableColumn(field="years", title="Year", formatter=HTMLTemplateFormatter()),
            TableColumn(field="populations", title="Population", formatter=NumberFormatter(format='0,0')),
            TableColumn(field="counties", title="County"),
        ]
    for w in phrase_split:
        columns.append(TableColumn(field=w, title=w,  formatter=NumberFormatter(format='0,0'))),
    city_table = DataTable(source=citySource, columns=columns, width=size, height=600,reorderable=False, index_position=None)
    
    countySource = ColumnDataSource(countyData)
    
    columns = [
            TableColumn(field="names", title="Name"),
            TableColumn(field="years", title="Year", formatter=HTMLTemplateFormatter()),
            TableColumn(field="populations", title="Population", formatter=NumberFormatter(format='0,0')),
        ]
    for w in phrase_split:
        columns.append(TableColumn(field=w, title=w,  formatter=NumberFormatter(format='0,0'))),
    county_table = DataTable(source=countySource, columns=columns, reorderable=False, index_position=None)
    
    cityTab = Panel(title="Cities", child=city_table)
    countyTab = Panel(title="Counties", child=county_table)
    tabs = Tabs(tabs=[cityTab, countyTab])

    resultsDiv = Div(text="""
                     <h1>{} out of {} cities have a match.</h1>
                     <h1>{} out of {} counties have a match.</h1>
                     """.format(uniqueCities, numCities, uniqueCounties, numCounties))
    
    popMap = Panel(title="Population", child=p2)
    outlineMap = Panel(title="Spatial", child=p)
    mapTabs = Tabs(tabs=[outlineMap, popMap])
    
    l = layout(column([row([mapTabs, resultsDiv]), tabs]))
    lScript,lDiv = components(l)
    cdn_js = CDN.js_files
    cdn_css = CDN.css_files

    return render_template('results.html',lScript=lScript,lDiv=lDiv)                                                                #render results page with map and table object as arguments



@app.route('/outp/<string:city>/<string:words>')                                                                                    #route for page containing highlighted pdf
def highlight_pdf(city,words):                                                                                                      #function for highlighting pdf phrases with pdf file name, list of words and phrase count as inputs

    complete_name = os.path.join("static/data/places", city)                                                                        #path for city pdf file
    doc = fitz.open(complete_name)                                                                                                  #create open pdf file object
    page_count= len(doc)                                                                                                            #find no. of pages in pdf               
    if "," in words:
        list_split=words.split(",")                                                                                                 #split wordlist by commas
    else:
        list_split=[words]                                                                                                          #if no commas means single word
    wordcount=len(list_split)
    text_instances = [" "] * wordcount                                                                                              #occurences of a phrase in a page
    for i in range(page_count):
        for k in range(wordcount):
            text_instances[k] = doc[i].searchFor(list_split[k],hit_max = 100)                                                            #search for the phrase in the page(maximum 100 occurences)
        for k in range(wordcount):      
            for inst in text_instances[k]:
                highlight = doc[i].addHighlightAnnot(inst)                                                                          #highlight all occurences of phrase
    highlighted_complete_name = os.path.join("static/data/pdfoutput","output.pdf")                                                  #path for highlighted pdf            
    doc.save(highlighted_complete_name)                                                                                             #save highlighted pdf
    doc.close()
    fht= 'window.location.href = "/static/data/pdfoutput/output.pdf";'                                                              #send highlighted pdf link
 
    fht = Markup(fht)                                                                                                               #make the link safe for sending to html
    
    return render_template('download.html',fht=fht)                                                                                 #render pdf file with the higlighted pdflink as argument
    

    
if __name__ == "__main__":                                                                                                          #run app on local host at port 5000 in debug mode
    
    app.run(host="0.0.0.0", port=5000, debug=True)
     



