#elasticsearch python file
import sys
from elasticsearch import Elasticsearch
import os
from pathlib import Path
import glob 
import re 
import json 
def index_everything():
	es = Elasticsearch('http://localhost:9200')
	wd = os.getcwd()
	data_dir = os.path.join(wd, 'data', 'plan_text')
	files = glob.glob(data_dir+'/*')
	key_hash_mapping = {}
	i = 0 
	for filepath in files:
		try: 
			txt = Path(filepath).read_text() 
		except:
			print(f'issue with filepath {filepath}')
			continue 
		key = os.path.basename(filepath)
		keyhash = i
		print(key, keyhash)
		key_hash_mapping[keyhash] = key
		es.index(index='test_4', id=keyhash, body={'text': txt, 'plan_name': key})
		i += 1
		if i >10:
			break 

	with open('key_hash_mapping.json', 'w') as fp:
		json.dump(key_hash_mapping, fp)


def search_contains_words(words):
	es = Elasticsearch('http://localhost:9200')
	search = es.search(index='test_4', body={'query': {'match': {'text': words}}})
	ids = []
	keys = []
	for hit in search['hits']['hits']:
		ids.append(int(hit['_id']))

	ids = [int(hit['_id']) for hit in search['hits']['hits']]
	return ids, search['hits']['total']['value'],

def search_contains_phrase(words):
	es = Elasticsearch('http://localhost:9200')
	search = es.search(index='test_4', body={'query': {'match_phrase': {'text': words}}})
	ids = []
	keys = []
	for hit in search['hits']['hits']:
		ids.append(int(hit['_id']))

	ids = [int(hit['_id']) for hit in search['hits']['hits']]
	return ids, search['hits']['total']['value'],


def my_search(query):

	phrase_list=re.findall(r'\"(.+?)\"',query)
	words_list = query.split('"')
	if not words_list:
		cw_ids = None
	else:
		cw_ids, _ = search_contains_words(' '.join(words_list))

	phrase_ids = cw_ids
	for phrase in phrase_list:
		ids, _ = search_contains_phrase(phrase)
		if phrase_ids is not None:
			phrase_ids = list(set(phrase_ids) & set(ids))
		else:
			phrase_ids = ids
	print("word_list", words_list)
	print("phrase_list", phrase_list)

	return phrase_ids

if __name__ == "__main__":
    index_everything()
    query = "the good dog"
    search_result_indices = my_search(query)
#    with open('key_hash_mapping.json', 'r') as fp:
#            data = json.load(fp)
#            my_dict = data

 #   results = list(map(lambda x:my_dict[str(x)], search_result_indices))
 #   print(results)

