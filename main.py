import os
import requests

def download_inaturalist_images(taxon_id, species_name, num_images=300):
    per_page = 100 
    page = 1
    downloaded = 0
    headers = {'User-Agent': 'Mozilla/5.0'}
    folder = species_name.replace(" ", "_")
    os.makedirs(folder, exist_ok=True)

    while downloaded < num_images:
        url = f"https://api.inaturalist.org/v1/observations?taxon_id={taxon_id}&per_page={per_page}&page={page}&order=desc&order_by=created_at"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch data for {species_name}. Status code: {response.status_code}")
            break
        data = response.json()
        results = data.get('results', [])
        if not results:
            print(f"No more observations found for {species_name}.")
            break
        for obs in results:
            photos = obs.get('photos', [])
            for photo in photos:
                if downloaded >= num_images:
                    break
                url = photo.get('url')
                if url:
                   
                    image_url = url.replace('square', 'original')
                    try:
                        img_data = requests.get(image_url, headers=headers).content
                        with open(f"{folder}/{species_name.replace(' ', '')}{downloaded + 1}.jpg", 'wb') as handler:
                            handler.write(img_data)
                        downloaded += 1
                        print(f"Downloaded {downloaded} images for {species_name}")
                    except Exception as e:
                        print(f"Error downloading image: {e}")
        page += 1

# Listf species with their taxon IDs
species_list = [
    
    {'name': 'Indian Rock Python', 'taxon_id': 32150},
    {'name': 'Reticulated Python', 'taxon_id': 491869},
    {'name': 'Green Tree Snake', 'taxon_id': 27214},
   
]

for species in species_list:
    download_inaturalist_images(species['taxon_id'], species['name'])