#elasticsearch python file
from elasticsearch import Elasticsearch
import os
from pathlib import Path
import glob 
import re 
import json
from collections import namedtuple
import csv 
from typing import Dict, List, Tuple
from collections import OrderedDict
from httplib2 import RedirectLimit
import pandas as pd
from datetime import date
#when you load this pacakge these global variables are defined 
#es = Elasticsearch('http://localhost:9200')
# es = Elasticsearch(
#    [os.environ.get('ES_HOST')],
#    http_auth=(os.environ.get('ES_USR'), os.environ.get('ES_PWD')),
#    scheme="https",
#    port=9243,
# )
es = Elasticsearch('http://localhost:9200')

def parse_filename(filename: str) -> str:
	"""	This function uses regular expressions to parse a filename. 
	filename format expected is CA_City-Rolling-Hills-Estates_2014.txt
	Args:
		filename (str): a filename (basepath of a filepath) that has the 
		format StateCode_CityORcounty-Place-Name_PlanYear.filetype
	Returns:
		Dict: Dictionarty containing filepath information 
		the keys are state, filename, is_city, place_name,
		plan_date, filetype
	"""		

	search_result = re.search(r'([A-z]{2})_(City|county)-([A-z-]*)_([0-9]{4}|nd).(txt|pdf|PDF.txt)', filename)
	assert search_result, 'invalid filename, must follow format State_CityORcounty-Place-Name_PlanYear.filetype'

	state = search_result.group(1)
	is_city = True if search_result.group(2) == 'City' else False
	place_name = re.sub('-',' ', search_result.group(3))
	plan_date = search_result.group(4)
	filetype = search_result.group(5)

	return {'state': state, 'filename': filename,'is_city': is_city,'place_name': place_name, 'plan_date': plan_date, 'filetype': filetype}

county_dict = None
city_dict = None 
def build_pop_dicts() -> None:
	"""Loads country csv and city csv into memory and builds 
	   a dictionary to map between place name and population
	"""	
	global county_dict
	global city_dict
	data_dir = os.path.join('static', 'data') 
	dict_dict = {}
	for filename in ['cityPopulations.csv', 'countyPopulations.csv']:
		file_dir = os.path.join(data_dir, filename)
		my_dict = {}
		with open(file_dir) as csvfile:
			r = csv.reader(csvfile)
			for row in r:
				my_dict[row[0]] = row[1:]
		dict_dict[filename] = my_dict
	county_dict = dict_dict['countyPopulations.csv']
	city_dict = dict_dict['cityPopulations.csv'] 	

def get_place_properties(is_city: bool, place_name: str) -> Dict:
	"""gets a place's properties
	Args:
		is_city (bool): A boolean for if the name belongs to a city or county
		place_name (str): the name of the place 
	Returns:
		dict: A dictionary of properties of the 
	"""	
	if county_dict is None or city_dict is None:
		build_pop_dicts()
	if is_city:
		return city_dict[place_name]
	else:
		return county_dict[place_name]

def get_max_index() -> int:
	"""Gets the next open index
	"""	
	return es.search(index='test_4', body={"_source": False})['hits']['total']['value']

def add_to_index(filepath:str) -> None:
	"""Adds a new file to the elasticsearch index
	Args:
		filepath (str): a filepath to a txt file general plan
	"""	
	
	i = get_max_index()

	try: 
		filename = os.path.basename(filepath)
		parsed_filename = parse_filename(filename)
		txt = Path(filepath).read_text()
		txt = re.sub(r'\s+', ' ', txt).lower()
	except Exception as e:
		print(f'issue with filepath {filepath} nothing added')
		print(e)
		return 

	print(i, filename)
	keyhash = i
	es.index(index='test_4', id=keyhash, body={'text': txt, 'filename': filename}, )


	with open('key_hash_mapping.json', 'r') as fp:
		hash_to_prop_mapping = json.load(fp)
	
	hash_to_prop_mapping[keyhash] = parsed_filename

	with open('key_hash_mapping.json', 'w') as fp:
		json.dump(hash_to_prop_mapping, fp)

def index_everything():
	"""Adds all of the txt files in the data directory to the elasticsearch index
	"""	
	global es
	global index_to_info_map
	wd = os.getcwd()
	es.indices.delete(index='test_4', ignore=[400, 404])
	data_dir = os.path.join(wd, 'static', 'data', 'places')
	filepaths = glob.glob(data_dir+'/*.txt')
	hash_to_prop_mapping = {}
	i = 0
	for filepath in filepaths:
		try: 
			filename = os.path.basename(filepath)
			parsed_filename = parse_filename(filename)
			txt = Path(filepath).read_text()
			txt = re.sub(r'\s+', ' ', txt).lower()
		except Exception as e:
			print(f'issue with filepath {filepath}')
			print(e)
			continue 
		print(i, filename)
		keyhash = i
		hash_to_prop_mapping[keyhash] = parsed_filename
		es.index(index='test_4', id=keyhash, body={'text': txt, 'filename': filename}, )
		i += 1
	with open('key_hash_mapping.json', 'w') as fp:
		json.dump(hash_to_prop_mapping, fp)
	index_to_info_map = None

def get_recentyears():
	plan_df = pd.read_json('key_hash_mapping.json', orient='index')
	plan_df.drop(['state','filename','filetype'], axis=1, inplace=True)

	city_df = plan_df[plan_df.is_city == True]
	county_df = plan_df[plan_df.is_city == False]
	city_df.sort_values(by=['place_name','plan_date'], ascending=[True,False], inplace=True)
	city_df.drop_duplicates(subset='place_name', keep='first', inplace=True)
	city_df["color"] = city_df["plan_date"].apply(assign_color)
	county_df.sort_values(by=['place_name','plan_date'], ascending=[True,False], inplace=True)
	county_df.drop_duplicates(subset='place_name', keep='first', inplace=True)
	county_df["color"] = county_df["plan_date"].apply(assign_color)

	path_to_recentcity = 'static/data/recent-cityplans.csv'
	path_to_recentcounty = 'static/data/recent-countyplans.csv'
	city_df.to_csv(path_to_recentcity)
	county_df.to_csv(path_to_recentcounty)

# Color Key: 1 - Green, 
# 2 - Yellow, 3 - Orange
# 4 - Red, 5 - Purple
def assign_color(plan_year: int):
	curr_year = date.today().year
	diff_in_year = curr_year - plan_year
	if (diff_in_year <= 3):
		return 1
	elif (diff_in_year > 3 and diff_in_year <= 5):
		return 2
	elif (diff_in_year > 5 and diff_in_year <= 8):
		return 3
	elif (diff_in_year > 8 and diff_in_year <= 15):
		return 4
	elif (diff_in_year > 15):
		return 5
	

def elastic_search(query) -> Tuple[List[int], List[float]]:
	"""Puts a query into elasticsearch and returns the ids and score
	Args:
		query (str): The elasticsearch query 
	Returns:
		Tuple(List[int], List[float]): ids of search results and their scores 
	"""	
	
	global es
	query_json = {"_source": False,
	"size":1000,        
	"query": {
    "simple_query_string" : {
        "query": query,
        "fields": ["text"],
        "default_operator": "and"
    }}}
	search = es.search(index='test_4' ,body=query_json, request_timeout=60) 
	ids = []
	scores = []
	for hit in search['hits']['hits']:
		ids.append(int(hit['_id']))
		scores.append(float(hit['_score']))

	# writes highlites to webpage 
	# include highlite in query
    # "highlight": {
	# 	"fields": {
	# 		"text": {}
	# 	}
	# },
	# ids = [int(hit['_id']) for hit in search['hits']['hits']]
	# webpage = ' <p>'.join(search['hits']['hits'][0]['highlight']['text'])
	# with open('/Users/dda/Desktop/mywebpage.html', 'w') as f:
	# 	f.write(webpage)
	print(search)
	return ids , scores


index_to_info_map = None
def map_keys_to_values(search_result_indices, key_to_hash_path='key_hash_mapping.json'):
	"""maps index to keys 
	Args:
		search_result_indices (List[int]): 
		key_to_hash_path (str, optional): [description]. Defaults to 'key_hash_mapping.json'.
	Returns:
		dict of info values realting to the keys, such as filename: [
	"""	
	global index_to_info_map
	if index_to_info_map is None:
		with open(key_to_hash_path, 'r') as fp:
			data = json.load(fp)
			my_dict = data
			index_to_info_map = my_dict
	else:
		my_dict = index_to_info_map

	return list(map(lambda x:my_dict[str(x)]['filename'], search_result_indices))

def map_index_to_vals(search_result_indices, key_to_hash_path='key_hash_mapping.json'):
	global index_to_info_map
	if index_to_info_map is None:
		with open(key_to_hash_path, 'r') as fp:
			data = json.load(fp)
			my_dict = data
			index_to_info_map = my_dict
	else:
		my_dict = index_to_info_map

	# print(index_to_info_map)
	return list(map(lambda x:my_dict[str(x)], search_result_indices))

def elastic_search_highlight(query):
	"""Puts a query into elasticsearch and returns the ids, score, hits and highlights
	This works by counting the number of <em> paris in the highlighted text. 
	Args:
		query (str): The elasticsearch query 
		page_num (int): [Optional] The page number
	Returns:
		Tuple(List[int], List[float], List[int], Dict[str]): ids, score, hits and highlights 
	"""	
	size = 1000
	num_of_chars = 450
	frag_count = 100
	max_offset = 100000000
	global es
	query_json = {"_source": False,
	"size": size,      
	"query":{
    "simple_query_string" : {
        "query": query,
        "fields": ["text"],
        "default_operator": "and"}
        }, 
        "highlight": {
			"pre_tags" : ["<mark>"],
    		"post_tags" : ["</mark>"],
		   	"fields": {
			   	"text": {
			   		"fragment_size" : num_of_chars,
			   		"number_of_fragments": frag_count,
			   		# "max_analyzed_offset": max_offset
			   	}
			}
      	},
		"fields": [ "filename" ]
	}

	search_with_highlights = es.search(index='test_4' ,body=query_json, request_timeout=30) 
	hit_count_dict = OrderedDict()
	highlight_list = {}
	ids = []
	scores = []
	for snipets in search_with_highlights["hits"]["hits"]:
		id = snipets["_id"]
		# highlight_list.append(snipets["highlight"]["text"])
		highlight_list[snipets["fields"]["filename"][0]] = snipets["highlight"]["text"]
		ids.append(int(snipets['_id']))
		scores.append(float(snipets['_score']))
		for snip in snipets["highlight"]["text"]:
			if id in hit_count_dict:
				hit_count_dict[id] += snip.count("mark>")//2
			else:
				hit_count_dict[id] = snip.count("mark>")//2

	hit_count_list = list(hit_count_dict.values())

	return (ids, scores, hit_count_list, highlight_list) 


if __name__ == "__main__":
	index_everything()
