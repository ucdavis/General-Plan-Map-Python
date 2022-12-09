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
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter
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

from datetime import date
from bokeh.models import Legend, LegendItem
from bokeh.models import FixedTicker

from bokeh.models import BasicTickFormatter
from bokeh.transform import linear_cmap,factor_cmap
import textract

import random
import glob
### BELOW NEEDED TO EXPORT BOKEH IMAGE FILES
# from bokeh.io import export_png
# from bokeh.io.export import get_screenshot_as_png
# from selenium import webdriver
# import chromedriver_binary
# import base64

app = Flask(__name__)  # create flask object
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # avoid storing cache
bootstrap = Bootstrap(app)  # create bootstrap object


@app.route('/', methods=['GET'])  # declare flask page url
def my_form():  # function for main index

    # return render_template('maintenance_progress.html')

    # Defining the color coding for the cities.
    color1 = "#2ca25f" # Green : Cities with plan updated less than 5 years ago.
    color2 = "#fec44f" # Yellow : Cities with plan updated 5-10 years ago.
    color3 = "#de2d26" # Red : Cities with plan updated 10-15 years ago.
    color4 = "#8856a7" # Purple : Cities with plan updated 15+ years ago.
    color0 = "#bdbdbd" # Grey : Cities with no data available.

    # Creating a mapper to map color_code -> color
    color_mapper = {
        0 : color0,
        1 : color1,
        2 : color2,
        3 : color3,
        4 : color4
    }

    # These dfs have the latest color for the places and their population and area too
    city_df = pd.read_csv('static/data/city_plans_files/city_updated_years_new.csv')
    county_df = pd.read_csv('static/data/city_plans_files/county_updated_years_new.csv')

    with open(os.path.join(geojson_path, 'map.geojson'), 'r') as f:
        my_str = f.read()
        spatial_map_for_city = json.loads(my_str)
        spatial_map_for_county = json.loads(my_str)

    county_map = fill_county_colors(spatial_map_for_county, county_df, color_mapper) 
    city_map = fill_city_colors(spatial_map_for_city, city_df, color_mapper)


    # Defining the bokeh map, with source as city_plans json file.
    TOOLS = ["hover", "pan", "wheel_zoom", "save"]

    # Defining county map
    county_spatial_map = figure(
        title="Map showing most recently updated plans in database:",
        x_axis_location = None,
        y_axis_location = None,
        tools = TOOLS,
        active_scroll = "wheel_zoom",
        tooltips = [("", "@county_name"), ("", "@last_year_updated_county")])

    county_spatial_map.grid.grid_line_color = None
    county_spatial_map.hover.point_policy = "follow_mouse"
    county_spatial_map_Geosource = GeoJSONDataSource(geojson = json.dumps(county_map))
    county_spatial_map.patches('xs',
                            'ys',
                            source = county_spatial_map_Geosource,
                            fill_color = 'color',
                            line_color = 'line_color')

    county_panel = Panel(title = "County Data", child = county_spatial_map)

    # Defining city map
    city_spatial_map = figure(
        title="Map showing most recently updated plans in database:",
        x_axis_location = None,
        y_axis_location = None,
        tools = TOOLS,
        active_scroll = "wheel_zoom",
        tooltips = [("", "@county_name"), ("", "@city_name"), ("", "@last_year_updated_city")])

    city_spatial_map.grid.grid_line_color = None
    city_spatial_map.hover.point_policy = "follow_mouse"
    city_spatial_map_Geosource = GeoJSONDataSource(geojson = json.dumps(city_map))
    city_spatial_map.patches('xs',
                            'ys',
                            source = city_spatial_map_Geosource,
                            fill_color = 'color',
                            line_color = 'line_color')

    city_panel = Panel(title = "City Data", child = city_spatial_map)

    map_tabs = Tabs(tabs = [city_panel, county_panel], css_classes=["table-results-div"], margin = (0, 0, 0, 0))
    map_layout = layout(column(map_tabs))
    map_script, map_div = components(map_layout)

    # Data for bar graphs
    city_plans_count = get_categories(city_df, 0)
    county_plans_count = get_categories(county_df, 0)
    city_population_count = get_categories(city_df, 1)
    county_population_count = get_categories(county_df, 1)
    city_area_count = get_categories(city_df, 2)
    county_area_count = get_categories(county_df, 2)

    # Defining the colors and categories for the bar plots
    colors = [color1, color2, color3, color4, color0]
    categories = ['0 - 5', '5 - 10', '10 - 15', '15 +', 'No data available']

    # PLOT 1
    # Number of plans vs year most recently updated: (city)
    source = ColumnDataSource(data=dict(categories=categories, city_plans_count=city_plans_count))
    plot1 = figure(x_range=categories, height=300, toolbar_location=None, title="Number of plans vs year most recently updated:",
              tools="hover", tooltips="Number of cities: @city_plans_count")
    plot1.vbar(x='categories', top='city_plans_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot1.xgrid.grid_line_color = None
    plot1.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot1.y_range.start = 0

    # PLOT 2
    # Number of plans vs year most recently updated: (county)
    source = ColumnDataSource(data=dict(categories=categories, county_plans_count=county_plans_count))
    plot2 = figure(x_range=categories, height=300, toolbar_location=None, title="Number of plans vs year most recently updated:",
              tools="hover", tooltips="Number of counties: @county_plans_count")
    plot2.vbar(x='categories', top='county_plans_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot2.xgrid.grid_line_color = None
    plot2.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot2.y_range.start = 0

    # PLOT 3
    # Population vs year most recently updated: (city)
    source = ColumnDataSource(data=dict(categories=categories, city_population_count=city_population_count))
    plot3 = figure(x_range=categories, height=300, toolbar_location=None, title="Population vs year most recently updated:",
              tools="hover", tooltips="Population count: @city_population_count")
    plot3.vbar(x='categories', top='city_population_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot3.xgrid.grid_line_color = None
    plot3.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot3.y_range.start = 0

    # PLOT 4
    # Population vs year most recently updated: (county)
    source = ColumnDataSource(data=dict(categories=categories, county_population_count=county_population_count))
    plot4 = figure(x_range=categories, height=300, toolbar_location=None, title="Population vs year most recently updated:",
              tools="hover", tooltips="Population count: @county_population_count")
    plot4.vbar(x='categories', top='county_population_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot4.xgrid.grid_line_color = None
    plot4.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot4.y_range.start = 0

    # PLOT 5
    # Land area vs year most recently updated: (city)
    source = ColumnDataSource(data=dict(categories=categories, city_area_count=city_area_count))
    plot5 = figure(x_range=categories, height=300, toolbar_location=None, title="Land area vs year most recently updated:",
              tools="hover", tooltips="Land covered (km. sq.): @city_area_count")
    plot5.vbar(x='categories', top='city_area_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot5.xgrid.grid_line_color = None
    plot5.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot5.y_range.start = 0

    # PLOT 6
    # Land area vs year most recently updated: (county)
    source = ColumnDataSource(data=dict(categories=categories, county_area_count=county_area_count))
    plot6 = figure(x_range=categories, height=300, toolbar_location=None, title="Land area vs year most recently updated:",
              tools="hover", tooltips="Land covered (km. sq.): @county_area_count")
    plot6.vbar(x='categories', top='county_area_count', width=0.9, source=source, line_color='white',
           fill_color=factor_cmap('categories', palette=colors, factors=categories))
    plot6.xgrid.grid_line_color = None
    plot6.yaxis.formatter = BasicTickFormatter(use_scientific=False)
    plot6.y_range.start = 0

    # Defining panels for each plot
    bar_panel_1 = Panel(title = "City Data", child = plot1)
    bar_panel_2 = Panel(title = "County Data", child = plot2)
    bar_panel_3 = Panel(title = "City Data", child = plot3)
    bar_panel_4 = Panel(title = "County Data", child = plot4)
    bar_panel_5 = Panel(title = "City Data", child = plot5)
    bar_panel_6 = Panel(title = "County Data", child = plot6)

    # Defining tabs for city and county plots together
    bar_tab_1_2 = Tabs(tabs = [bar_panel_1, bar_panel_2], css_classes=["table-results-div"], margin = (0, 0, 0, 0))
    bar_tab_3_4 = Tabs(tabs = [bar_panel_3, bar_panel_4], css_classes=["table-results-div"], margin = (0, 0, 0, 0))
    bar_tab_5_6 = Tabs(tabs = [bar_panel_5, bar_panel_6], css_classes=["table-results-div"], margin = (0, 0, 0, 0))

    # STATS
    # Get stats
    stats_dict = get_stats(city_df, county_df)

    # Creating the scripts and divs to render on HTML
    layout_plot_1_2 = layout(column(bar_tab_1_2))
    layout_plot_3_4 = layout(column(bar_tab_3_4))
    layout_plot_5_6 = layout(column(bar_tab_5_6))

    plot_1_2_script, plot_1_2_div = components(layout_plot_1_2)
    plot_3_4_script, plot_3_4_div = components(layout_plot_3_4)
    plot_5_6_script, plot_5_6_div = components(layout_plot_5_6)

    cdn_js = CDN.js_files
    cdn_css = CDN.css_files

    return render_template('index.html', 
        scripts = [map_script, plot_1_2_script, plot_3_4_script, plot_5_6_script], 
        divs = [map_div, plot_1_2_div, plot_3_4_div, plot_5_6_div], 
        stats = [stats_dict["file_count"], stats_dict["total_pages"], stats_dict["total_words"], 
        stats_dict["missing_cities"], stats_dict["missing_counties"]])  # return index page


def get_stats(city_df, county_df):
    """This function will create the city_plans.geojson file iff it does not exist. It takes the color_mapper
    as input (unused function, now creating the maps using city_updated_years.csv and same for county)
    Args:
        color_mapper (dict): the color coding mapped in dictionary format
    Returns:
        city_plans (geojson): city_plans geojson data for the bokeh map
    """
    missing_cities = []
    missing_counties = []

    #check if the stats file exists
    path_to_file = "static/data/city_plans_files/stats.json"
    file_exists = os.path.exists(path_to_file)

    if file_exists :
        with open(path_to_file, 'r') as openfile:
            stats_dict = json.load(openfile)

    else:
        # List and count of files
        DIR = "static/data/places"
        list_of_pdfs = [name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name)) and 
        (name.endswith(".pdf") or name.endswith(".PDF"))]
        file_count = len(list_of_pdfs)

        # Page count
        total_pages = 0
        for name in list_of_pdfs:
            file = open(os.path.join(DIR, name), 'rb')
            try:
                read_pdf = PdfFileReader(file)
                total_pages += read_pdf.numPages
            except:
                continue

        # Word count
        total_words = 0
        for name in list_of_pdfs:
            try:
                text = textract.process(os.path.join(DIR, name)).decode('utf-8')
                words = re.findall(r"[^\W_]+", text, re.MULTILINE)
                total_words += len(words)
            except:
                continue

        # Finding missing cities and counties
        with open("static/data/city_plans_files/complete_cities_counties.json", 'r') as openfile:
            complete_city_county_dict = json.load(openfile)

        complete_county_list = complete_city_county_dict['counties']
        complete_city_list = complete_city_county_dict['cities']

        # In case of cities, the missing cities are the cities whose 'last_updated_color' is 0 i.e. there
        # is no data available for them. So we need to iterate through whole city_df and select such cities
        # If the city name is not in the present list, then obviously we dont have its data and we add it to 
        # the missing_cities list too.
        # SAME LOGIC for counties

        present_county_list = list(county_df.iloc[:, 1]) # Get the county list from county_df
        present_city_list = list(city_df.iloc[:, 1]) # Get the city list from city_df

        for city in complete_city_list:
            try:
                index = present_city_list.index(city)
                # check if this city has no data available
                if city_df.at[index, 'last_updated_color'] == 0:
                    missing_cities.append(city)
            except:
                # city not in list so implies it is missing
                missing_cities.append(city)

        for county in complete_county_list:
            try:
                index = present_county_list.index(county)
                # check if this city has no data available
                if county_df.at[index, 'last_updated_color'] == 0:
                    missing_counties.append(county)
            except:
                # city not in list so implies it is missing
                missing_counties.append(county)

        # Coverting the city and county names from caps to title format.
        missing_cities = [item.title() for item in missing_cities]
        missing_counties = [item.title() for item in missing_counties]
        
        # Create the dictionary and save to local
        stats_dict = {
            "file_count" : file_count,
            "total_pages" : total_pages,
            "total_words" : total_words,
            "missing_cities" : missing_cities,
            "missing_counties" : missing_counties
        }

        stats_json_object = json.dumps(stats_dict, indent=4)
        with open(path_to_file, "w") as outfile:
            outfile.write(stats_json_object)

    return stats_dict


def get_categories(df, mode):
    """This function will take in dataframe of cities or counties and return the required information array counts 
    according to the mode passed along it.
    Args:
        df : city_df or county_df
        mode : 0,1,2; refer comments below to get to know about each mode.
    Returns:
        counts (array): the required count for each category. (0-5, 5-10, 10-15, 15+, No data available)
    """
    counts = [0, 0, 0, 0, 0]
    total_population = 0
    total_area = 0
    todays_date = date.today()
    
    # mode = 0 is for the number of plans up to date
    if mode == 0:
        for index, row in df.iterrows():
            update_range = todays_date.year - row['year_updated']
            if pd.isnull(row['year_updated']):
                counts[4] += 1
            elif update_range >= 15:
                counts[3] += 1
            elif update_range < 15 and update_range >= 10:
                counts[2] += 1
            elif update_range < 10 and update_range >= 5:
                counts[1] += 1
            elif update_range < 5 and update_range >= 0:
                counts[0] += 1
    
    # mode = 1 is for the population distribution among these up to date plans
    elif mode == 1:
        for index, row in df.iterrows():
            update_range = todays_date.year - row['year_updated']
            total_population += int(row['population'])
            if pd.isnull(row['year_updated']):
                counts[4] += int(row['population'])
            elif update_range >= 15:
                counts[3] += int(row['population'])
            elif update_range < 15 and update_range >= 10:
                counts[2] += int(row['population'])
            elif update_range < 10 and update_range >= 5:
                counts[1] += int(row['population'])
            elif update_range < 5 and update_range >= 0:
                counts[0] += int(row['population'])
    
    # mode = 2 is for the land area covered by the up to date plans
    else:
        for index, row in df.iterrows():
            update_range = todays_date.year - row['year_updated']
            total_area += int(row['area'])
            if pd.isnull(row['year_updated']):
                counts[4] += int(row['area'])
            elif update_range >= 15:
                counts[3] += int(row['area'])
            elif update_range < 15 and update_range >= 10:
                counts[2] += int(row['area'])
            elif update_range < 10 and update_range >= 5:
                counts[1] += int(row['area'])
            elif update_range < 5 and update_range >= 0:
                counts[0] += int(row['area'])
            
    return counts


def create_city_plans_json(color_mapper):
    """This function will create the city_plans.geojson file iff it does not exist. It takes the color_mapper
    as input (unused function, now creating the maps using city_updated_years.csv and same for county)
    Args:
        color_mapper (dict): the color coding mapped in dictionary format
    Returns:
        city_plans (geojson): city_plans geojson data for the bokeh map
    """
    geojson_path = os.path.join('static', 'data', 'CA_geojson')
    map_json = None

    with open(os.path.join(geojson_path, 'map.geojson'), 'r') as f:
        my_str = f.read()
        map_json = json.loads(my_str)

    city = gpd.read_file("static/data/city_plans_files/ca-places-boundaries/CA_Places_TIGER2016.shp")
    city.to_crs("EPSG:4326")

    county = gpd.read_file("static/data/city_plans_files/CA_Counties/CA_Counties_TIGER2016.shp")
    county.to_crs("EPSG:4326")

    combined = pd.read_csv("static/data/city_plans_files/California_Incorporated_Cities_2022.csv")

    gp = pd.read_csv("static/data/city_plans_files/Cities.csv")

    city.drop('geometry', inplace=True, axis=1)
    county.drop('geometry', inplace=True, axis=1)

    city1 = city.filter(['NAME'])
    city1['NAME'] = city1['NAME'].str.upper()
    city1.columns = ['CITY']

    county1 = county.filter(['NAME'])
    county1['NAME'] = county1['NAME'].str.upper()
    county1.columns = ['COUNTY']

    combined['CITY'] = combined['CITY'].str.upper()
    combined['COUNTY'] = combined['COUNTY'].str.upper()
    combined = combined.filter(['COUNTY', 'CITY'])
    combined = combined.merge(city1, on='CITY', how='left')
    combined = combined.merge(county1, on='COUNTY', how='left')
    combined = combined.drop_duplicates(['CITY','COUNTY'],keep='first')


    todays_date = date.today()
    gp['updated'] = 1
    gp_clean = gp.filter(['City_Names', 'updated', 'GP_Last_Updated'])
    gp_clean.rename(columns = {'City_Names':'CITY', 'GP_Last_Updated':'year_updated'}, inplace = True)
    gp_clean['CITY'] = gp_clean['CITY'].str.upper()
    gp_clean['year_updated'] = pd.to_numeric(gp_clean['year_updated'], errors='coerce')
    gp_clean['last_updated'] = todays_date.year - gp_clean['year_updated']
    gp_clean['last_updated_color'] = gp_clean.apply(lambda row: get_range_color(row), axis=1)

    final_combined = combined.merge(gp_clean, on='CITY', how='left')
    final_combined = final_combined.drop_duplicates(['CITY','COUNTY'],keep='first')
    final_combined = final_combined.filter(['CITY', 'year_updated','last_updated_color'])

    map_json = fill_city_colors(map_json, final_combined, color_mapper)

    with open(os.path.join(geojson_path, 'city_plans.geojson'), 'w') as f:
        geojson.dump(map_json, f)

    return map_json

def get_range_color(row):
    """This function will provide the color code for a particular city. 
    Args:
        row (dataframe): a row containing info about one city of the final_combined dataframe
    Returns:
        int: color code of the city
    """
    if pd.isnull(row['last_updated']):
        return 0
    elif row['last_updated'] >= 15:
        return 4
    elif row['last_updated'] < 15 and row['last_updated'] >= 10:
        return 3
    elif row['last_updated'] < 10 and row['last_updated'] >= 5:
        return 2
    else:
        return 1


def fill_city_colors(json_dict, final_combined, color_mapper,
                        blank_county_color = 'white', blank_county_outline = '#b3b3b3'):
    """This function will take in the geojson and color it according to the color mapper and city data
    Args:
        json_dict (dict): map geojson
        final_combined (dataframe): details about all the cities (cleaned)
        color_mapper (dict): the color coding mapped in dictionary format
    Returns:
        json_dict (dict): updated geojson according to color_mapper and final_combined
    """
    mapper = {}
    for index, row in final_combined.iterrows():
        # Getting the last year updated for every city from the dataframe.
        year = ""
        if pd.isna(row['year_updated']):
            year = "No data found"
        else:
            year = str(int(row['year_updated']))
        mapper[row['CITY']] = [row['last_updated_color'], year]
        
    city_names = mapper.keys()

    for feature in json_dict['features']:
        if feature['properties']['name'].upper() in city_names:
            feature['properties']['city_name'] = "City name: " + feature['properties']['name']
            feature['properties']['county_name'] = ""
            feature['properties']['last_year_updated_city'] = "Last Year updated: " + mapper[feature['properties']['name'].upper()][1]
            feature['properties']['color'] = color_mapper[mapper[feature['properties']['name'].upper()][0]]
            feature['properties']['line_color'] = blank_county_outline
        
        else:
            feature['properties']['city_name'] = ""
            feature['properties']['county_name'] = "County name: " + feature['properties']['name']
            feature['properties']['last_year_updated_city'] = ""
            feature['properties']['color'] = blank_county_color
            feature['properties']['line_color'] = blank_county_outline

        # city_name , county_name and last_year_updated_city are new fields being added so they can
        # be used to print values through tooltips in bokeh map code.

    return json_dict


def fill_county_colors(json_dict, county_df, color_mapper,
                       blank_city_color = 'white', blank_county_color = 'white',
                       blank_city_outline = '#dedede', blank_county_outline = '#b3b3b3',
                       match_city_fill_color = "#d47500", match_city_outline = '#dedede',
                       match_county_fill_color = "#00a4a6", match_county_outline = '#b3b3b3'):
    """This function will take in the geojson and color it according to the color mapper and county data
    Args:
        json_dict (dict): map geojson
        final_combined (dataframe): details about all the cities (cleaned)
        color_mapper (dict): the color coding mapped in dictionary format
    Returns:
        json_dict (dict): updated geojson according to color_mapper and final_combined
    """
    mapper = {}
    for index, row in county_df.iterrows():
        year = ""
        if pd.isna(row['year_updated']):
            year = "No data found"
        else:
            year = str(int(row['year_updated']))
        mapper[row['COUNTY'] + ' COUNTY'] = [row['last_updated_color'], year]
        
    county_names = mapper.keys()
    
    county_dict = {}
    county_dict['type'] = json_dict['type']
    county_dict['features'] = []

    for feature in json_dict['features']:
        if feature['properties']['name'].upper() in county_names:
            feature['properties']['city_name'] = ""
            feature['properties']['county_name'] = "County name: " + feature['properties']['name']
            feature['properties']['last_year_updated_county'] = "Last Year updated: " + mapper[feature['properties']['name'].upper()][1]
            feature['properties']['color'] = color_mapper[mapper[feature['properties']['name'].upper()][0]]
            feature['properties']['line_color'] = blank_county_outline
            county_dict['features'].append(feature)
        elif feature['properties']['name'].upper().endswith('COUNTY'):
            feature['properties']['city_name'] = ""
            feature['properties']['county_name'] = "County name: " + feature['properties']['name']
            feature['properties']['last_year_updated_county'] = "Last Year updated: No data found" 
            feature['properties']['color'] = color_mapper[0]
            feature['properties']['line_color'] = blank_county_outline
            county_dict['features'].append(feature)            
            
    # county_name and last_year_updated_county are new fields being added so they can
    # be used to print values through tooltips in bokeh map code.
            
    return county_dict


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
        query = "\"" + query + "\""
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
    twitQuery = re.sub('"','',wordinput)
    uniqueCities = len(set(cityData["names"]))
    uniqueCounties = len(set(countyData["names"]))
    numCities = 482
    numCounties = 58
    shareDiv = Div(text = """
                        <h1> Share Results: </h1>
                        <a href="https://twitter.com/share?ref_src=twsrc%5Etfw" class="twitter-share-button" data-size="large" data-text="{} out of {} California cities mention &#39;{}&#39; in their General Plans." data-show-count="false">Tweet</a><script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
                        """.format(uniqueCities, numCities, twitQuery),
                        margin = (0, 0, 0, 40),
                        css_classes = ["share-div"])
    resultsDiv = Div(text = """
                     <span class='darker-text-color'>{} </span><span class='white-text-color'>out of </span><span class='darker-text-color'>{} </span><span class='white-text-color'>cities mention </span><span class='darker-text-color'>'{}'</span><br/><br/>
                     <span class='darker-text-color'>{} </span><span class='white-text-color'>out of </span><span class='darker-text-color'>{} </span><span class='white-text-color'>counties mention </span><span class='darker-text-color'>'{}'</span>
                     """.format(uniqueCities, numCities, twitQuery, uniqueCounties, numCounties, twitQuery),
                     margin = (40, 0, 20, 30),
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
    p_timeline = figure(plot_height = 400,
                        plot_width = 700,
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

    page_layout = layout(column([row([column(mapTabs), column([shareDiv, resultsDiv])]), tabs, p_timeline]))
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
    # import pdb; pdb.set_trace()

    # remove files from the pdfoutput folder first
    files = glob.glob('static/data/pdfoutput/*')
    for f in files:
        os.remove(f)

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

    # breakpoint()
    pdf_output_filename = city + '_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + '.pdf'
    highlighted_complete_name = os.path.join("static/data/pdfoutput",pdf_output_filename)
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
