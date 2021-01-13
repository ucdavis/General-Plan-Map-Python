# General-Plan-Map

## How to Access

You can access a working version of this application [here](http://critical-data-analysis.org/shiny/general-plan-map/R/).

## About

Each city and county in California is required to produce a General Plan, a document that outlines and commits local governments to long-term development goals. Planning laws in the State of California mandate that every General Plan address a common set of issues, including Land Use, Conservation, and Housing. However, such laws do not specify where in the General Plan such issues need to be addressed or the format of the Plan overall. Thus, while General Plans offer the most comprehensive blueprint for future visioning of cities and counties throughout California, the structure and format of the Plans vary considerably across cities and counties. This makes it difficult to readily compare planning approaches across the state, to comparatively evaluate progress towards planning goals, and to set benchmarks for policy success. 
 
This project is developing a platform for readily querying and extracting snippets of information about issues such as planned housing across all General Plans. Currently, there are no states that have such a public database for querying General Plans state-wide. The platform is expected to become a key policy implementation and enforcement infrastructure for the California OPR, a resource for community developers in collaborative planning, and a valuable information source for community members and researchers. 

### The Tool

The General Plan Map provides access to the text of all California city General Plans and enables users to query for a single search term to determine the plans in which that term is referenced. Upon searching, the tool filters a map to the cities in CA with General Plans that reference the word, offering a geospatial representation of the term's use. The tool also links to the plans that reference the term. Users can click through to the plans and search within the page for the term. 

### Longer-Term Goals

* Archive historical general plans for each city in order to be able to track changes in plans over time
* Add county plans to the map, and allow users to toggle between the two
* Expand search functionality beyond a single word towards phrases
* Link to PDFs of the general plans vs. unformatted text
* Streamline the addition of new plans to the database

## Contributors

* [Catherine Brinkley](https://humanecology.ucdavis.edu/catherine-brinkley), Project Lead
* [Lindsay Poirier](https://sts.ucdavis.edu/people/lpoirier), Critical Data Analysis Lead
* Dexter Antonio, Lead Developer
* Makena Dettmann
* Sujoy Ghosh
* Margaret Riley

## How to Contribute

1. File an issue via this repo's [issue queue](https://github.com/Hack-for-California/General-Plan-Map/issues).

2. Write code to fix issues or to create new features. When contributing code, please be sure to:

  * Fork this repository, modify the code (changing only one thing at a time), and then issue a pull request for each change.
  * Follow the project's coding style (using K&R-style indentation and bracketing, commenting above each feature, and using snake case for variables).
  * Test your code locally before issuing a pull request.
  * Clearly state the purpose of your change in the description field for each commit.

## Architecture

textsearch.py contains most of the code for searching the pdfs, creating the maps and tables, and displaying the maps and tables. upload.py contins the code for uploading new pdfs, emailing the recipient of choice, and generating the searchable text document. 

The data, including the shapefiles and population data for both the cities and counties are found in /static/data/. The code also looks for a folder named places inside /static/data/ which is where .pdfs and their corresponding .txt documents will be stored.

The .html templates are stored in /templates/. These templates contain references which are passed from textsearch.py. There are also dependencies on .css and .js code stored in /static/cssjs/css and /static/cssjs/js respectively. The images found on the site are stored in /static/images/.

### Dependencies
* [flask](https://flask.palletsprojects.com/en/1.1.x/)
* [bokeh](https://docs.bokeh.org/en/latest/index.html)
* [PyMuPDF](https://pypi.org/project/PyMuPDF/)
* [pytesseract](https://pypi.org/project/pytesseract/)
* [fitz](https://pypi.org/project/fitz/)
* [shapely](https://pypi.org/project/Shapely/)
* [pydrive](https://pythonhosted.org/PyDrive/)
* [pandas](https://pandas.pydata.org/)
* [geopandas](https://geopandas.org/)

## Copyrights

Please see [license](https://github.com/Hack-for-California/General-Plan-Map/blob/master/LICENSE) file for details.

## Cite As

Brinkley, C; Poirier, L; Antonio, D (2020) California City General Plan Database Mapping Tool. [http://critical-data-analysis.org/shiny/general-plan-map/R/](http://critical-data-analysis.org/shiny/general-plan-map/R/)
[![DOI](https://zenodo.org/badge/238352230.svg)](https://zenodo.org/badge/latestdoi/238352230)

## Have Questions?
Contact [hack-for-california@ucdavis.edu](mailto:hack-for-california@ucdavis.edu)
