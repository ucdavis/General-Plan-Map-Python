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

#when you load this pacakge these global variables are defined 
es = Elasticsearch('http://localhost:9200')


def parse_filename(filename: str) -> str:
	"""	This function uses regular expressions to parse a filename. 
	filename format expected is CA_City-Rolling-Hills-Estates_2014.txt
	Args:
		filename (str): a filename (basepath of a filepath) that has the 
		format StateCode_CityORcounty_Place-Name_PlanYear.filetype

	Returns:
		Dict: Dictionarty containing filepath information 
		the keys are state, filename, is_city, place_name,
		plan_date, filetype
	"""		

	search_result = re.search(r'([A-z]{2})_(City|county)-([A-z-]*)_([0-9]{4}|nd).(txt|pdf|PDF.txt)', filename)
	assert search_result, 'invalid filename, must follow format State_CityORcounty_Place-Name_PlanYear.filetype'

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
	wd = os.getcwd()
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
	search = es.search(index='test_4' ,body=query_json) 
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

	return list(map(lambda x:my_dict[str(x)], search_result_indices))




if __name__ == "__main__":
	# index_everything()
	search_result_indices, score = elastic_search('City of Buellton General Plan Land Use Acreage')
	map_keys_to_values([3])	
	#print(index_to_info_map)
	result = map_keys_to_values(search_result_indices)

	# build_pop_dicts()
	# search = es.search(index='test_3', body={'query': {'match_phrase': {'text': "made to reduce greenhouse"}}})
	# ids = []
	# scores = []
	# for hit in search['hits']['hits']:
	# 	ids.append(int(hit['_id']))
	# 	scores.append(float(hit['_score']))

	#print(ids)



