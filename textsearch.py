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
from bokeh.models import LogColorMapper, ColumnDataSource, DataTable, DateFormatter, TableColumn, NumberFormatter, HTMLTemplateFormatter, Div, SingleIntervalTicker, Range1d
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
### BELOW NEEDED TO EXPORT BOKEH IMAGE FILES
# from bokeh.io import export_png
# from bokeh.io.export import get_screenshot_as_png
# from selenium import webdriver
# import chromedriver_binary
# import base64

app = Flask(__name__)  # create flask object
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # avoid storing cache
bootstrap = Bootstrap(app)  # create bootstrap object


@app.route('/')  # declare flask page url
def my_form():  # function for main index
    return render_template('index.html')  # return index page


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
    zipped.sort(key=lambda x: x[2], reverse=True)
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
        # search things
        self.score = score
        self.hits = hits
        self.highlights = highlights

        # additional properties
        self.county = county
        self.population = 0
        self.cityType = city_type

        self.pdf_filename = self.filename.split('.')[0] + '.pdf'
        parsed_query = self.parse_query(query)

        # allows user to click on year on webpage's result table; 
        #### uncomment below in order to link to 'highlight_pdf' function
        self.year = '<p hidden>'+self.plan_date+'</p> <a href="../outp/'+self.pdf_filename+'/'+parsed_query+'" target="_blank">'+self.plan_date+"</a>"
        #### uncomment below in order to link to 'display_results' function
        # self.year = '<p hidden>'+self.plan_date+'</p> <a href="../outp/'+self.place_name+'/'+self.pdf_filename+'/'+parsed_query+'" target="_blank">'+self.plan_date+"</a>"
        
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
                       blank_city_color = 'white', blank_county_color = 'white',
                       blank_city_outline = '#dedede', blank_county_outline = '#b3b3b3',
                       match_city_fill_color = "#d47500", match_city_outline = '#dedede',
                       match_county_fill_color = "#00a4a6", match_county_outline = '#b3b3b3'):

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
            # ****** NOT YET IMPLEMENTED ******
            # else: # a county
            #     feature['properties']['color'] = blank_county_color
            #     feature['properties']['line_color'] = blank_county_outline

geojson_path = os.path.join('static', 'data', 'CA_geojson')

with open(os.path.join(geojson_path, 'map.geojson'), 'r') as f:
    my_str = f.read()
    spatial_map = json.loads(my_str)

with open(os.path.join(geojson_path, 'pop_map.geojson'), 'r') as f:
    pop_map = json.load(f)


@app.route('/results/', methods=['GET'])

def index_search_box():
    """The code for the search box functionality
    Returns:
        str : html webpage
    """

    #==============================================================================
    #Get results for the query
    #==============================================================================
    wordinput = " "  # initialize string input for search
    wordinput = request.args.get('query')  # get input from request form on webpage

    try:
        results = getResults(wordinput)
    except ValueError:  # appears when getResults tries to zip no results
        return render_template('noresult.html')

    #==============================================================================
    #Initialize variables
    #==============================================================================

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
    maxCityYearCount = 0
    maxCountyYearCount = 0
    maxYearCount = 0

    #==============================================================================
    #Append population to results
    #==============================================================================
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

    #==========================
    #Plots for mapping results
    #==========================
    change_json_colors(spatial_map, results)

    change_json_colors(pop_map, results)

    TOOLS = ["hover", "pan", "wheel_zoom", "save"]
    p_pop_map = figure(
        x_axis_location = None,
        y_axis_location = None,
        x_axis_type = "mercator",
        y_axis_type = "mercator",
        tools = TOOLS,
        tooltips = [("Name", "@name")]
        )
    p_pop_map.grid.grid_line_color = None
    p_pop_map.hover.point_policy = "follow_mouse"
    p_pop_map_GeoSource = GeoJSONDataSource(geojson = json.dumps(pop_map))
    p_pop_map.patches('xs',
                        'ys',
                        source = p_pop_map_GeoSource,
                        fill_color = 'color',
                        line_color = 'line_color')

    p_spatial_map = figure(
        x_axis_location = None,
        y_axis_location = None,
        tools = TOOLS,
        tooltips = [("Name", "@name")])

    p_spatial_map.grid.grid_line_color = None
    p_spatial_map.hover.point_policy = "follow_mouse"
    p_spatial_map_Geosource = GeoJSONDataSource(geojson = json.dumps(spatial_map))
    p_spatial_map.patches('xs',
                            'ys',
                            source = p_spatial_map_Geosource,
                            fill_color = 'color',
                            line_color = 'line_color')

    popMap = Panel(title = "Population", child = p_pop_map)
    outlineMap = Panel(title = "Spatial", child = p_spatial_map)
    mapTabs = Tabs(tabs = [outlineMap, popMap])

    #==============================================================================
    #Create dictionary and data frame of results for summary, timeline, and chart
    #==============================================================================

    cityData = dict(
        names = [res.cityName for res in cityResults],
        years_href = [res.year for res in cityResults],
        years = [res.plan_date for res in cityResults],
        types = [res.cityType for res in cityResults],
        fNames = [res.pdf_filename for res in cityResults],
        populations = [res.population for res in cityResults],
        counties = [res.county for res in cityResults],
        hits = [res.hits for res in cityResults]
        )

    countyData = dict(
        names = [res.cityName for res in countyResults],
        years_href = [res.year for res in countyResults],
        years = [res.plan_date for res in countyResults],
        types = [res.type for res in countyResults],
        fNames = [res.pdf_filename for res in countyResults],
        populations = [res.population for res in countyResults],
        hits = [res.hits for res in countyResults]
        )

    #====================================================
    #Div with summary counts of cities mentioning query
    #====================================================
    shareDiv = Div(text = """
                        <h1> Share Results: </h1>
                        <a href="https://twitter.com/share?ref_src=twsrc%5Etfw" class="twitter-share-button" data-size="large" data-text="{} out of {} California cities mention &#39;{}&#39; in their General Plans." data-show-count="false">Tweet</a><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
                        """.format(uniqueCities, numCities, wordinput),
                        margin = (0, 0, 0, 30),
                        css_classes = ["share-div"])
    uniqueCities = len(set(cityData["names"]))
    uniqueCounties = len(set(countyData["names"]))
    numCities = 482
    numCounties = 58
    resultsDiv = Div(text = """
                     <span class='darker-text-color'>{} </span><span class='white-text-color'>out of </span><span class='darker-text-color'>{} </span><span class='white-text-color'>cities mention </span><span class='darker-text-color'>'{}'.</span><br/><br/>
                     <span class='darker-text-color'>{} </span><span class='white-text-color'>out of </span><span class='darker-text-color'>{} </span><span class='white-text-color'>counties mention </span><span class='darker-text-color'>'{}'.</span>
                     """.format(uniqueCities, numCities, wordinput, uniqueCounties, numCounties, wordinput),
                     margin = (30, 0, 20, 30),
                     css_classes=["results-div"])

    #====================================================
    #Plots for timelines of results
    #====================================================
    citydf = pd.DataFrame.from_dict(cityData)
    #Count the number of plans that mentioned the query per year, sort it by year, and set the column names to years and counts
    cityYearsData = citydf['years'].value_counts().sort_index().rename_axis('years').reset_index(name = 'counts')
    cityYearsData = cityYearsData.loc[cityYearsData["years"] != "nd"]
    cityYearsData['years'] = cityYearsData['years'].astype(int)

    #Reindex city years data frame filling in missing consecutive years and setting count to 0
    if not cityYearsData.empty:
        cityYearsData = cityYearsData.set_index('years').reindex(range(cityYearsData.years.min(),
                                            cityYearsData.years.max()+1), fill_value = 0).reset_index()

    countydf = pd.DataFrame.from_dict(countyData)
    #Count the number of plans that mentioned the query per year, sort it by year, and set the column names to years and counts
    countyYearsData = countydf['years'].value_counts().sort_index().rename_axis('years').reset_index(name = 'counts')
    countyYearsData = countyYearsData.loc[countyYearsData["years"] != "nd"]
    countyYearsData['years'] = countyYearsData['years'].astype(int)

    #Reindex county years data frame filling in missing consecutive years and setting count to 0
    if not countyYearsData.empty:
        countyYearsData = countyYearsData.set_index('years').reindex(range(countyYearsData.years.min(),
                                            countyYearsData.years.max()+1), fill_value = 0).reset_index()


    #Calculate the max year count to set the height of the y-axis
    if cityYearsData.empty:
        maxCityYearCount = 0
    else:
        maxCityYearCount = max(cityYearsData['counts'])

    if countyYearsData.empty:
        maxCountyYearCount = 0
    else:
        maxCountyYearCount = max(countyYearsData['counts'])

    maxYearCount = max(maxCityYearCount, maxCountyYearCount)

    #Set column data sources for plotting
    source_city = ColumnDataSource(cityYearsData)
    source_county = ColumnDataSource(countyYearsData)

    TOOLTIPS = [
        ("Year", "@years"),
        ("Count", "@counts"),
    ]

    #Create timeline figure
    p_timeline = figure(plot_height = 300,
                        plot_width = 350,
                        toolbar_location = None,
                        x_axis_label = "Year",
                        y_axis_label = "Plans Mentioning '" + wordinput + "'",
                        y_minor_ticks = 2,
                        margin = (30, 0, 0, 0),
                        tools = "",
                        tooltips = TOOLTIPS)
    p_timeline.circle(x = 'years', y = 'counts', source = source_city, color = "#d47500", legend_label="City", name = "city_timeline")
    p_timeline.line(x = 'years', y = 'counts', source = source_city, line_width = 2, color = "#d47500", line_alpha = 0.5)
    p_timeline.circle(x = 'years', y = 'counts', source = source_county, color = "#00a4a6", legend_label="County", name = "county_timeline")
    p_timeline.line(x = 'years', y = 'counts', source = source_county, line_width=2, color = "#00a4a6", line_alpha = 0.5)
    p_timeline.yaxis.ticker = SingleIntervalTicker(interval = 1)
    p_timeline.y_range = Range1d(0, maxYearCount)
    p_timeline.xaxis.axis_label_text_font = 'poppins'
    p_timeline.xaxis.axis_label_text_font_style = 'normal'
    p_timeline.yaxis.axis_label_text_font = 'poppins'
    p_timeline.yaxis.axis_label_text_font_style = 'normal'
    p_timeline.xaxis.axis_line_color = "#b3b3b3"
    p_timeline.yaxis.axis_line_color = "#b3b3b3"
    p_timeline.yaxis.minor_tick_line_color = None
    p_timeline.legend.location = "top_left"



    #====================================================
    #Table of results with links to plans
    #====================================================
    citySource = ColumnDataSource(cityData)
    size = 850

    columns = [
            TableColumn(field = "names", title = "Name"),
            TableColumn(field = "years_href", title = "Year", formatter = HTMLTemplateFormatter()),
            TableColumn(field = "populations", title = "Population", formatter = NumberFormatter(format = '0,0')),
            TableColumn(field = "counties", title = "County"),
            TableColumn(field = "hits", title = "Count")
        ]

    city_table = DataTable(source = citySource,
                            columns = columns,
                            width = size,
                            height = 600,
                            reorderable = False,
                            index_position = None,
                            row_height = 40)

    countySource = ColumnDataSource(countyData)

    columns = [
            TableColumn(field = "names", title = "Name"),
            TableColumn(field = "years_href", title = "Year", formatter = HTMLTemplateFormatter()),
            TableColumn(field = "populations", title = "Population", formatter = NumberFormatter(format = '0,0')),
            TableColumn(field = "hits", title = "Count")
        ]
    county_table = DataTable(source = countySource,
                                columns = columns,
                                reorderable = False,
                                index_position = None,
                                row_height = 40)

    cityTab = Panel(title = "Cities", child = city_table)
    countyTab = Panel(title = "Counties", child = county_table)
    tabs = Tabs(tabs = [cityTab, countyTab], css_classes=["table-results-div"], margin = (30, 0, 30, 0))

    #====================================================
    #Layout of the page
    #====================================================

    page_layout = layout(column([row([column(mapTabs), column([shareDiv, resultsDiv, p_timeline])]), tabs]))
    lScript,lDiv = components(page_layout)
    cdn_js = CDN.js_files
    cdn_css = CDN.css_files

    return render_template('results.html', lScript = lScript, lDiv = lDiv)

@app.route('/outp/<string:city>/<string:words>')

def highlight_pdf(city, words):
    """Function responsible for highlighting pdf words
    Args:
        pdf (str): the name of the pdf file
        words (str): comma seperated phrases to highlight
    Returns:
        str: webpages
    """
    complete_name = os.path.join("static/data/places", city)
    doc = fitz.open(complete_name)
    page_count= len(doc)  # find no. of pages in pdf
    if "," in words:
        list_split=words.split(",")
    else:
        list_split=[words]  # if no commas in wordlist, single word

    wordcount=len(list_split)
    text_instances = [" "] * wordcount  # occurences of any phrase in a page
    for i in range(page_count):
        for k in range(wordcount):
            text_instances[k] = doc[i].searchFor(list_split[k],hit_max = 100)  # look for search phrase in page (max. 100 occurences)
            if (len(text_instances[k]) != 0):
                # list returned by searchFor can be used directly as argument to highlight
                doc[i].addHighlightAnnot(text_instances[k])

    highlighted_complete_name = os.path.join("static/data/pdfoutput","output.pdf")
    doc.save(highlighted_complete_name)
    doc.close()

    # set link for highlighted pdf and make safe to send to html
    fht= 'window.location.href = "/static/data/pdfoutput/output.pdf";'
    fht = Markup(fht)

    # render highlighted pdf file
    return render_template('download.html',fht=fht)


if __name__ == "__main__":

    # from werkzeug.contrib.profiler import ProfilerMiddleware
    # app.config['PROFILE'] = True
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run(host="0.0.0.0", port=5000, debug=True)
