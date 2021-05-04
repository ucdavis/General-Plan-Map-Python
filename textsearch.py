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
import es 
import re
import geojson 

app = Flask(__name__)                                                                                                               #create flask object
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0                                                                                         #avoid storing cache
bootstrap = Bootstrap(app)                                                                                                          #create bootstrap object


@app.route('/')                                                                                                                     #declare flask page url
def my_form():                                                                                                                      #function for main index
    return render_template('index.html')                                                                                            #return index page


def getResults(wordinput):                                                                                                          
    """This function is used to take word input in the searchbox, query elasticsearch,
    and then return the results. 
    Args:
        wordinput (str): an elastic search query

    Returns:
        str: html doc that will be displayed 
    """    
    results = []
    query = wordinput

    ids, scores, hits, highlights = es.elastic_search_highlight(query)
    # sort by hits 
    zipped = list(zip(ids, scores, hits, highlights))
    zipped.sort(key=lambda x: x[2])
    ids, scores, hits, highlights = zip(*zipped)
    ids = list(ids)
    scores = list(scores)
    hits = list(hits)
    highlights = list(highlights)
        

    result_props = es.map_index_to_vals(ids)
    for score, result_prop, hit, highlight in zip(scores, result_props, hits, highlights):
        result_prop = result_prop.copy()
        result_prop['query'] = query 
        result_prop['score'] = score
        result_prop['hits'] = hit
        result_prop['highlights'] = highlight
        new_result = Result(**result_prop)
        try:
            place_props = es.get_place_properties(new_result.is_city, new_result.place_name)
        except:
            print('error with file %s result ignored '%new_result.filename)
            continue 

        if new_result.is_city:
            new_result.cityType = place_props[0]
            new_result.county = place_props[1]
            new_result.population = int(place_props[2])
        else:
            new_result.cityType = 'county'
            new_result.county = new_result.place_name
            new_result.population = int(place_props[0])

        results.append(new_result)

    
        
    return results

    
class Result:
    """This results class stores the data of a single search 'hit'.
    """    
    def __init__(self, state, filename, is_city, place_name, plan_date, filetype,  query, county='na', population=0, city_type='na', score=0, hits=0, highlights=None):
        # place properties 
        self.state = state
        self.filename = filename
        self.is_city = is_city
        self.place_name = place_name
        self.plan_date = plan_date
        self.filetype = filetype
        #search things 
        self.score = score
        self.hits = hits
        self.highlights = highlights
        
        # additional properties 
        self.county = county
        self.population = 0
        self.cityType = city_type

        self.pdf_filename = self.filename.split('.')[0] + '.pdf'
        parsed_query = self.parse_query(query) 
        # this self.year is the html that will be displayed around the year 
        # it will link to a function that will highlight the word occuraces in the file
        self.year = '<p hidden>'+self.plan_date+'</p> <a href="outp/'+self.pdf_filename+'/'+parsed_query+'" target="_blank">'+self.plan_date+"</a>"
    
    def parse_query(self, query):
        """This function parses a query to add commas between words except
        for words that are a phrase (indicated by their quotes)]

        Args:
            query (str): query to parse

        Returns:
            [type]: a parsed query that can be used in html  
        """
        phrases_in_quotes = re.findall(r'\"(.+?)\"',query)
        non_quotes = re.sub(r'"',"", re.sub(r'\"(.+?)\"', '', query))
        all_words = re.findall('[A-z]+', non_quotes)
        list_split = phrases_in_quotes + all_words
        return ','.join(list_split)

    @property
    def cityName(self):
        """This is a property tag that is useful for parts of legacy code

        Returns:
            str: place name  
        """        
        return self.place_name
    
    @property
    def type(self):
        """returns a str describing the category of place
        Returns:
            str: either "City" or "county"
        """        
        if self.is_city:
            return 'City'
        else:
            return 'county'

def change_json_colors(json_dict, results, 
                       blank_city_color='white', blank_county_color='white', 
                       blank_city_outline='#dedede', blank_county_outline='#b3b3b3',
                       match_city_fill_color="#d47500", match_city_outline='#dedede',
                       match_county_fill_color="#00a4a6", match_county_outline='#b3b3b3'):     
    
    result_names = []
    result_dict = {}
    for result in results:
        if result.is_city:
            name = result.cityName
        else:
            name = result.cityName + ' County'
        result_names.append(name)
        result_dict[name] = result
    
    for feature in json_dict['features']:
        if feature['properties']['name'] in result_names:
            if result_dict[feature['properties']['name']].is_city:
                feature['properties']['color'] = match_city_fill_color
                feature['properties']['line_color'] = match_city_outline
            else:  # a county 
                feature['properties']['color'] = match_county_fill_color
                feature['properties']['line_color'] = match_county_outline 
 
        else: # no match
            feature['properties']['color'] = blank_city_color
            feature['properties']['line_color'] = blank_city_outline
            # else: # a county  not yet implimtented 
            #     feature['properties']['color'] = blank_county_color
            #     feature['properties']['line_color'] = blank_county_outline

geojson_path = os.path.join('static', 'data', 'CA_geojson')
with open(os.path.join(geojson_path, 'map.geojson'), 'r') as f:  
    my_str = f.read()  
    my_map = json.loads(my_str)

with open(os.path.join(geojson_path, 'pop_map.geojson'), 'r') as f:  
    pop_map = json.load(f)

@app.route('/', methods=['POST'])                                                                                                   #connect search form to html page
def index_search_box():                                                                                                             #function for accepting search input
    """The code for the search box functionality 

    Returns:
        str : html webpage
    """    
    wordinput=" "                                                                                                                   #initialize string input for search
    wordinput=request.form['u']                                                                                                     #set name for search form
    results = getResults(wordinput)
    matched_city_names = []
    matched_county_names = []
    cityResults = []
    countyResults = []
    countyPops = {}
    cityPops = {}
    uniqueCities = 0
    uniqueCounties = 0
    maxCityPop = 1
    maxCountyPop = 1
    for res in results:
        if res.is_city:
            cityResults.append(res)
            matched_city_names.append(res.place_name) 
            cityPops[res.place_name] = res.population
            if res.population > maxCityPop:
                maxCityPop = res.population
        else:
            countyResults.append(res)
            countyPops[res.place_name] = res.population
            matched_county_names.append(res.place_name) 
            if res.population > maxCountyPop:
                maxCountyPop = res.population
    
    if len(results) < 1:
        return render_template('noresult.html')

    change_json_colors(my_map, results) 
    change_json_colors(pop_map, results)
    geosource = GeoJSONDataSource(geojson = json.dumps(my_map))

    TOOLS = ["hover", "pan", "wheel_zoom", "save"]
    p2 = figure(
        x_axis_location=None, y_axis_location=None,
        x_axis_type="mercator", y_axis_type="mercator",
        tools=TOOLS,
        tooltips=[("Name", "@name")]
        )
    p2.grid.grid_line_color = None
    p2.hover.point_policy = "follow_mouse"
    p2GeoSource = GeoJSONDataSource(geojson=json.dumps(pop_map))
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
        fNames=[res.pdf_filename for res in cityResults],
        populations = [res.population for res in cityResults],
        counties = [res.county for res in cityResults],
        hits = [res.hits for res in cityResults]
        )

    countyData = dict(
        names=[res.cityName for res in countyResults],
        years=[res.year for res in countyResults],
        types=[res.type for res in countyResults],
        fNames=[res.pdf_filename for res in countyResults],
        populations=[res.population for res in countyResults],
        hits = [res.hits for res in countyResults]
        )
    
    uniqueCities = len(set(cityData["names"]))
    uniqueCounties = len(set(countyData["names"]))
    
    
    citySource = ColumnDataSource(cityData)
    
    columns = [
            TableColumn(field="names", title="Name"),
            TableColumn(field="years", title="Year", formatter=HTMLTemplateFormatter()),
            TableColumn(field="populations", title="Population", formatter=NumberFormatter(format='0,0')),
            TableColumn(field="counties", title="County"),
            TableColumn(field="hits", title="Count")
        ]
    city_table = DataTable(source=citySource, columns=columns, width=size, height=600,reorderable=False, index_position=None)
    
    countySource = ColumnDataSource(countyData)
    
    columns = [
            TableColumn(field="names", title="Name"),
            TableColumn(field="years", title="Year", formatter=HTMLTemplateFormatter()),
            TableColumn(field="populations", title="Population", formatter=NumberFormatter(format='0,0')),
            TableColumn(field="hits", title="Count")
        ]
    county_table = DataTable(source=countySource, columns= columns, reorderable=False, index_position=None)
    
    cityTab = Panel(title="Cities", child=city_table)
    countyTab = Panel(title="Counties", child=county_table)
    tabs = Tabs(tabs=[cityTab, countyTab])

    numCities = 482 
    numCounties = 58 
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
def highlight_pdf(city, words):
    """Function responsible for highlighting pdf words

    Args:
        city (str): the name of the city
        words (str): comma seperated phrases to highlight

    Returns:
        str: webpages
    """    
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
    
    # from werkzeug.contrib.profiler import ProfilerMiddleware
    # app.config['PROFILE'] = True
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run(host="0.0.0.0", port=5002, debug=True)
