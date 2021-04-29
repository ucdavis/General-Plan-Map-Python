# Install Guide

This guide will walk you through the process of installing a local version of the general plan mapper to test your contributions before making a pull request. It will start with X, Y, Z.

# 1. Clone the repo

Start by cloning the repo to your local machine. You can do this by calling `git pull git@github.com:Hack-for-California/General-Plan-Map-Python.git` if you have an ssh key associated with your Github account, otherwise you can use `git pull https://github.com/Hack-for-California/General-Plan-Map-Python.git`, but know with this method you will need to sign in every time you want to push or pull your code. You should not download the repo in zip format, as that will sever the connection between the files and the Github repo, making it more troublesome to push or pull later.

# 2. Set up your working branch

Whenever you are making changes to a code repo, it is best practice to work on a separate branch, then merge your code in later. This makes and changes clearly and easily revesible. To start a branch open the project directory in some terminal application (on Windows usualyl git bash, on mac the normal terminal). You will want to make sure you are basing your work off of the `dev` branch, rather than the default `main`. To make sure this is the case, first make sure you have all branches in your local repo by running `git pull --all`. Once that is done, switch to dev using `git checkout dev`. From there, you can create a new branch which will be based on your current branch of dev. To do this run `git checkout -b <NAME OF BRANCH>` using whatever short name for the branch that works for you, and describes your intended changes. If you type `git status` it should now say you are on your new branch. Use `git push origin <NAME OF BRANCH>` to register your new branch on Github. From here on, you can just use `git push` to send commits as normal.

# 3. Switch the disply port

Before you start working on your changes, remember to change the port the mapper will be dispalyed in. You can do this by editing `textsearch.py` and editing the final line of code (`app.run(host="0.0.0.0", port=5000, debug=True)`). You want to change the port from `5000` to another `5002`, as that is what all colaborators use for testing the dev sites.

# 4. Get the current version running

Before you start making changes, we want to assure the current verion can run on your machine (so we know what broke it if it won't run later!). 