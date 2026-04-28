import requests, json
from pathlib import Path
import pandas as pd
import io


def process_api_request(url):
	try:
		response = requests.get(url)
		response.raise_for_status()

		response_json = response.json()
		return response_json
	except requests.exceptions.HTTPError as http_err:
		print(f"Erreur HTTP détectée : {http_err}")
	except Exception as e:
		print(f"Error: {str(e)}")
		return None


def get_all_json_data(url):
	response_json = process_api_request(url_datagouv + '?page=1&page_size=100')
	final_data = response_json['data']
	print("Page 1 récupérée")

	next_url = response_json['links']['next']

	i = 1
	while next_url:
		response_json = process_api_request(next_url)
		final_data.extend(response_json['data'])

		i += 1
		print(f"Page {i} récupérée")
		next_url = response_json['links']['next']
		
	return final_data


def get_datagouv_data(filepath, url):

	if Path(filepath).exists():
		print('Le dataset existe déjà')
	else:
		data = get_all_json_data(url)

		if data:
			with open(filepath, "w") as file:
				json.dump(data, file)


url_datagouv = "https://tabular-api.data.gouv.fr/api/resources/79b5cac4-4957-486b-bbda-322d80868224/data/"
filepath = 'data/src/src_datagouv/election_2022.json'


# get_datagouv_data(filepath, url_datagouv)