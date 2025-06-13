import requests

class TMDBApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def search_tv_series(self, query):
        """Search for TV series and return results"""
        url = f"{self.base_url}/search/tv"
        params = {
            'query': query,
            'include_adult': False,
            'language': 'en-US',
            'page': 1
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"TMDB API Error: {str(e)}")
            return []

    def get_tv_details(self, tmdb_id):
        """Get detailed information about a TV series"""
        url = f"{self.base_url}/tv/{tmdb_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"TMDB API Error: {str(e)}")
            return {}