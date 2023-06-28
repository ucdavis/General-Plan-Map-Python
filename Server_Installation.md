# Installing the PlanSearch Tool on Linux VM

This document goes over the step by step installation of PlanSearch Tool on a linux VM.
Four main steps:
- Install Anaconda
- Get the code from Github
- Transfer data files
- Configure Gunicorn and Nginx

#### For installing Anaconda through terminal, follow the below steps:
Create a `temp` directory in the user directory to download the Anaconda installer.
Get the latest Anaconda installer URL from https://www.anaconda.com/download (Right click on the download button and copy the URL). Use curl to download the installer in the temp directory and name is anaconda.sh.
```sh
mkdir temp
cd /temp
curl https://repo.anaconda.com/archive/Anaconda3-2023.03-1-Linux-x86_64.sh --output anaconda.sh
```
You can do verification of the installer using SHA-256 checksum.
```sh
sha256sum anaconda.sh
```
The output will look similar to:
```sh
fedf9e340039557f7b5e8a8a86affa9d299f5e9820144bd7b92ae9f7ee08ac60  anaconda.sh
```
Now run the bash script.
```sh
bash anaconda.sh
```
Keep pressing enter, accept the terms and conditions. Press enter to allow installation on the default location.
> Enter "yes" to "initialize Anaconda3 by running conda init".

Activate the installation by sourcing the bashrc file.
```sh
source ~/.bashrc
```
Congratulations! Anaconda has been installed on the VM. Now delete the temp directory as the installer is no longer required.
```sh
rm -rf temp
```

#### Importing code from Github.
Create a directory `server_code` in the user folder.
Clone the repository from Github.
```sh
git clone https://github.com/Hack-for-California/General-Plan-Map-Python.git
```
You should see all the files. Run `git branch` to check if the current working branch is "new_server". Now run the below commands to setup an upstream and pull all branches.
```sh
git remote add origin https://github.com/ucdavis/General-Plan-Map-Python.git
git remote set-url origin https://github.com/ucdavis/General-Plan-Map-Python.git
git pull --all
```
Now, create the conda environment.
```sh
conda create --name gpenv --file requirements.txt
```
Conda will create an environment named `gpenv`. Run the below command to activate the gpenv environment:
```sh
conda activate gpenv
```

#### Installing Elasticsearch
We will follow the installation of Elasticsearch with Debian package.
Run the following commands:
```sh
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg
```
```sh
sudo apt-get install apt-transport-https
```
```sh
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
```
```sh
sudo apt-get update && sudo apt-get install elasticsearch
```
Enable automatic creation of system indices
```sh
action.auto_create_index: .monitoring*,.watches,.triggered_watches,.watcher-history*,.ml*
```
Running elasticsearch using systemd. Very important.
```sh
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl enable elasticsearch.service
```
Now we can start, restart and stop elasticsearch using the following commands:
```sh
sudo systemctl start elasticsearch.service
sudo systemctl restart elasticsearch.service
sudo systemctl stop elasticsearch.service
```
I will share a configuration file for elasticsearch. Make sure the `/etc/elasticsearch/elasticsearch.yml` file on server looks like that in terms of configurations. Then restart the elasticsearch server.
Now run the following command to make sure the elasticsearch server is running:
```sh
curl localhost:9200
```

#### Transfer data files
Increase the VM disk space to avoid issues in the future. We have always doubled the disk space.
All the PDFs and TXT files have to be uploaded to the server. We will use `scp` to achieve this. The files should go in the `/static/data/places` directory.
The files are already available on the CAES Remote Desktop in the C-drive inside `server_files` folder.
Use the following command on CMD of the CAES Remote Desktop to transfer the files. Create the private key (.pem) using the puttygen tool.
```sh
scp -r -i <PRIVATE_KEY_PATH> <FILES_PATH> user_name@<IP_ADDRESS>:server_code/static/data/places
```
At the end, all the files (around 2.5k files) should be present in the places directory.
Also create `pdfoutput` and `temp` in `static/data` folder.

#### Transferring other important files to the server
Below is the list of some important files that are to be transferred to the server:
- passw (`../server_code/passw`)
- .env (`../server_code/.env`)
- mycreds.txt (`../server_code/mycreds.txt`)
- stats.json (`../server_code/static/data/city_plans_files/stats.json`)
- client_secrets.json (`../server_code/client_secrets.json`)
You should use the same scp command to transfer these files. I will share them with you guys according to your preferred way. These files are not to be shared on open internet.

#### Initial setup
Change the directory to `server_code`. Make sure you have activated the `gpenv` environment.
Start a python instance. Just run `python`.
Download the sample files for bokeh.
```py
import bokeh
bokeh.sampledata.download()
```
Now, we will build the elasticsearch index. Again, in a python instance, run the following commands:
```py
import es
es.index_everything()
```
You should see a list of all the files and their IDs. Elasticsearch index is ready now.

#### Configuring Gunicorn and Nginx
Install nginx
```sh
sudo apt update
sudo apt install nginx
```
Gunicorn is already installed. Make sure you have the `gpenv` environment activated.
Run the following command to check:
```sh
gunicorn --bind 0.0.0.0:5000 wsgi:app
```
Now we will create a service for gunicorn. Please switch to root user for the following procedures. (`sudo su`)\
Go to `/etc/systemd/system` and create a `flask_gunicorn.service` file. Enter the configuration details similar to the one I will share with you. The user_name and locations have to be updated according to your user.
Run the following command after creating the file:
```sh
sudo systemctl daemon-reload
sudo systemctl enable flask_gunicorn.service
sudo systemctl start flask_gunicorn.service
```
Also, a socket file must be created in the `server_code` directory. It will have a `.sock` extension. We have now successfully created a gunicorn service. Time to configure our Nginx server to route these requests to the gunicorn service.

Go to the default configuration file of nginx (`/etc/nginx/sites-available/default`) and replace the contents with the nginx configuration file I will share with you. Please keep in mind to change the locations and user_names according to the server.
Provide full access to Nginx through the VM firewall:
```sh
sudo ufw allow 'Nginx Full'
```
Now restart and reload Nginx.
```sh
sudo systemctl reload nginx
sudo systemctl restart nginx
```
Check if the services is running properly by running this command:
```sh
sudo systemctl status flask_gunicorn.service
sudo systemctl status nginx
```

Test if the website is accessible and working fine by opening https://plansearch.caes.ucdavis.edu/ on the browser.

#### Congratulations!! This pretty much wraps up the installation process for the PlanSearch tool website.
There is a small process for the Admin portal, but I am still trying to work on that on VM3. We can go over that process once the tool is up and running.