# start by pulling the python image
FROM python:3.8

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# switch working directory
WORKDIR /app

RUN apt-get update

RUN apt-get install -y libgdal-dev

RUN pip install GDAL==3.2.2.1

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

# Need to download the bokeh sample data
RUN python -c "import bokeh.sampledata; bokeh.sampledata.download()"

# install gunicorn server
RUN pip install gunicorn

# copy all content from the local file to the image
COPY . /app

# todo, run flask app on port specified here
ENV PORT 5000
EXPOSE 5000

# run txtsearch with gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "textsearch:app"]