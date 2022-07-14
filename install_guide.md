# Install Guide

This guide will walk you through the process of installing a local version of the general plan mapper to test your contributions before making a pull request. It will start with X, Y, Z.

# 1. Clone the repo

Start by cloning the repo to your local machine. You can do this by calling `git pull git@github.com:Hack-for-California/General-Plan-Map-Python.git` if you have an ssh key associated with your Github account, otherwise you can use `git clone https://github.com/Hack-for-California/General-Plan-Map-Python.git`, but know with this method you will need to sign in every time you want to push or pull your code. You should not download the repo in zip format, as that will sever the connection between the files and the Github repo, making it more troublesome to push or pull later.

# 2. Set up your working branch

Whenever you are making changes to a code repo, it is best practice to work on a separate branch, then merge your code in later. This makes and changes clearly and easily reversible. To start a branch open the project directory in some terminal application (on Windows usually git bash, on mac the normal terminal). You will want to make sure you are basing your work off of the `dev` branch, rather than the default `main`.

To make sure this is the case, first make sure you have all branches in your local repo by running `git pull --all`. Once that is done, switch to dev using `git checkout dev`. From there, you can create a new branch which will be based on your current branch of dev. To do this run `git checkout -b <NAME OF BRANCH>` using whatever short name for the branch that works for you, and describes your intended changes. If you type `git status` it should now say you are on your new branch. Use `git push origin <NAME OF BRANCH>` to register your new branch on Github. From here on, you can just use `git push` to send commits as normal.

# 3. Switch the display port

Before you start working on your changes, remember to change the port the mapper will be displayed in. You can do this by editing `textsearch.py` and editing the final line of code (`app.run(host="0.0.0.0", port=5000, debug=True)`). You want to change the port from `5000` to another `5002`, as that is what all collaborators use for testing the dev sites.

# 4. Prepare your python environment

Before you can run any code, you will need to set up a python environment with all the required modules. You can use the `environment.yml` file in the base directory of the project to do so in conjunction with `conda`. If you do now have `conda` installed, you will need to do so. When you are ready to create your `conda` environment, navigate to the base directory of the project and run `conda env create -f environment.yml`. This will create a conda environment named `gpenv`.

Once the environment is set up, you can activate it at any time using `conda activate gpenv`. You will need to do this whenever you want to run code related to this project.

**(NOTE)** If this does not work you can try using a `venv` instead. To do so go to your home directory and create the env using `python -m venv gpenv`, then enter `source /gpenv/bin/activate` to activate the environment. Once started, navigate to the project directory and use `cat requirements.txt | xargs -n 1 pip install` to install the required modules.

# 5. Install Elastic Search

Before you can run the General Plan Mapper locally, you will need to install elasticsearch locally. Please follow the directions available [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html).

Once you have installed ElasticSearch, you will need to start it before you launch the General Plan Mapper. The method of starting ElasticSearch depends on how you installed it. Please see [this guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/starting-elasticsearch.html) to find the method for your situation.

# 6. Installing Bokeh sample data

Before you can run the repo, you need to download the example bokeh datasets. First start a python instance by calling `python` within the `gpenv` environment. You will know you are in python when the input changes into `>>>`. Once in python run `import bokeh` then `bokeh.sampledata.download()`.

# 7. Download data files

You will need to download all the current data files from [the google drive](https://drive.google.com/drive/u/2/folders/1E6-I1oL4DX88TYxI59TBN_lOJtp0vMzR). Right click on the places folder and hit download. It will zip the entire directory and download it. Once it is finished, open the zip and place all the contents into the `./static/data/` directory (so there should be a folder at `./static/data/places` which contains several `.txt` and `.pdf` files).

# 8. Build the index

Next you will need to build the index for elastic search. To do so start python while in the `gpenv` environment by calling `python`, then `import es` to import the elastic search functions from `es.py`. Open a new additional terminal window to start the ElasticSearch server. See section 5 on how to start the ElasticSearch server. Next enter `es.index_everything()`. You should see the names of several text files and associated numbers pass through your terminal.

# 9. Get the current version running

Before you start making changes, we want to assure the current version can run on your machine (so we know what broke it if it won't run later!). To try running the program start the general plan mapper using `python textsearch.py`. It should then start up an instance of the mapper on your local machine. You can see it my going to a web browser and entering `localhost:5002`. Try searching for "water", if a map of California shows up, you're all good!

**(NOTE)** If things aren't working, try running `curl -X PUT http://localhost:9200/test_4/_settings -H 'Content-Type: application/json' -d '{   "index" : {     "highlight.max_analyzed_offset" : 10000000   } }'` in a terminal while elasticsearch is running.

# 10. Make your changes
