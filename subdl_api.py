import requests
import json
import traceback
from pathlib import Path

class SubdlAPI:
    # Complete language mapping with names
    LANGUAGES = {
        "AR": "Arabic",
        "BR_PT": "Brazillian Portuguese",
        "DA": "Danish",
        "NL": "Dutch",
        "EN": "English",
        "FA": "Farsi/Persian",
        "FI": "Finnish",
        "FR": "French",
        "ID": "Indonesian",
        "IT": "Italian",
        "NO": "Norwegian",
        "RO": "Romanian",
        "ES": "Spanish",
        "SV": "Swedish",
        "VI": "Vietnamese",
        "SQ": "Albanian",
        "AZ": "Azerbaijani",
        "BE": "Belarusian",
        "BN": "Bengali",
        "ZH_BG": "Big 5 code",
        "BS": "Bosnian",
        "BG": "Bulgarian",
        "BG_EN": "Bulgarian/English",
        "MY": "Burmese",
        "CA": "Catalan",
        "ZH": "Chinese BG code",
        "HR": "Croatian",
        "CS": "Czech",
        "NL_EN": "Dutch/English",
        "EN_DE": "English/German",
        "EO": "Esperanto",
        "ET": "Estonian",
        "KA": "Georgian",
        "DE": "German",
        "EL": "Greek",
        "KL": "Greenlandic",
        "HE": "Hebrew",
        "HI": "Hindi",
        "HU": "Hungarian",
        "HU_EN": "Hungarian/English",
        "IS": "Icelandic",
        "JA": "Japanese",
        "KO": "Korean",
        "KU": "Kurdish",
        "LV": "Latvian",
        "LT": "Lithuanian",
        "MK": "Macedonian",
        "MS": "Malay",
        "ML": "Malayalam",
        "MNI": "Manipuri",
        "PL": "Polish",
        "PT": "Portuguese",
        "RU": "Russian",
        "SR": "Serbian",
        "SI": "Sinhala",
        "SK": "Slovak",
        "SL": "Slovenian",
        "TL": "Tagalog",
        "TA": "Tamil",
        "TE": "Telugu",
        "TH": "Thai",
        "TR": "Turkish",
        "UK": "Ukranian",
        "UR": "Urdu"
    }

    # Language mapping with numeric IDs - only includes languages supported by Subdl API
    LANGUAGE_MAP = {
        'EN': '1',    # English
        'AR': '2',    # Arabic
        'FA': '3',    # Persian/Farsi
        'TR': '4',    # Turkish
        'BN': '5',    # Bengali
        'UR': '6',    # Urdu
        'HI': '7',    # Hindi
        'ID': '8',    # Indonesian
        'ML': '9',    # Malayalam
        'TA': '10',   # Tamil
        'BR_PT': '11',# Brazilian Portuguese
        'DA': '12',   # Danish
        'NL': '13',   # Dutch
        'FI': '14',   # Finnish
        'FR': '15',   # French
        'IT': '16',   # Italian
        'NO': '17',   # Norwegian
        'RO': '18',   # Romanian
        'ES': '19',   # Spanish
        'SV': '20',   # Swedish
        'VI': '21',   # Vietnamese
        'SQ': '22',   # Albanian
        'AZ': '23',   # Azerbaijani
        'BE': '24',   # Belarusian
        'ZH': '25',   # Chinese
        'HR': '26',   # Croatian
        'CS': '27',   # Czech
        'ET': '28',   # Estonian
        'KA': '29',   # Georgian
        'DE': '30',   # German
        'EL': '31',   # Greek
        'HE': '32',   # Hebrew
        'HU': '33',   # Hungarian
        'IS': '34',   # Icelandic
        'JA': '35',   # Japanese
        'KO': '36',   # Korean
        'LV': '37',   # Latvian
        'LT': '38',   # Lithuanian
        'MK': '39',   # Macedonian
        'MS': '40',   # Malay
        'PL': '41',   # Polish
        'PT': '42',   # Portuguese
        'RU': '43',   # Russian
        'SR': '44',   # Serbian
        'SK': '45',   # Slovak
        'SL': '46',   # Slovenian
        'TH': '47',   # Thai
        'UK': '48'    # Ukrainian
    }

    def __init__(self):
        self.token = self._get_token()
        
    def _get_token(self):
        """Get subdl token from settings.json"""
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                token = settings.get('subdl_api_key')
                if not token:
                    self._report("No subdl API key found in settings.json")
                    return None
                return token
        except FileNotFoundError:
            self._report("settings.json file not found")
            return None
        except json.JSONDecodeError:
            self._report("settings.json is not a valid JSON file")
            return None

    def get_nid(self):
        """Get a unique ID from subdl API"""
        headers = {'token': self.token}
        response = requests.get('https://api3.subdl.com/user/getNId', headers=headers)
        if response.ok:
            data = response.json()
            if data.get('ok'):
                return data.get('n_id')
        self._report(f"Failed to get NID from subdl: {response.text}")
        return None

    def upload_subtitle_file(self, subtitle_file):
        """Upload a subtitle file to subdl"""
        headers = {'token': self.token}
        with open(subtitle_file, 'rb') as f:
            files = {'subtitle': f}
            response = requests.post(
                'https://api3.subdl.com/user/uploadSingleSubtitle', 
                headers=headers, 
                files=files
            )
            if response.ok:
                data = response.json()
                if data.get('ok'):
                    return data.get('file', {}).get('file_n_id')
        self._report(f"Failed to upload subtitle file to subdl: {response.text}")
        return None

    def complete_upload(self, upload_data):
        """Complete the subtitle upload process"""
        headers = {
            'token': self.token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Validate language code
        if not upload_data.get('language') in self.LANGUAGES:
            self._report(f"Invalid language code: {upload_data.get('language')}")
            return False

        # Ensure releases is a list
        releases = upload_data.get('release', [])
        if isinstance(releases, str):
            releases = [releases]
        
        form_data = {
            'file_n_ids': json.dumps([upload_data['file_n_id']]),
            'tmdb_id': upload_data['tmdb_id'],
            'type': 'tv',
            'quality': 'web',
            'production_type': '2',
            'name': upload_data['name'],
            'releases': json.dumps(releases),
            'framerate': upload_data.get('framerate', '23.976'),  # Use provided framerate or default
            'comment': upload_data['comment'],
            'lang': upload_data['language'],
            'season': upload_data['season'],
            'hi': 'false',
            'is_full_season': 'false',
            'n_id': upload_data['n_id'],
            'tags': json.dumps(['subdl_pyuploader'])
        }
        
        try:
            response = requests.post(
                'https://api3.subdl.com/user/uploadSubtitle',
                headers=headers,
                data=form_data
            )
            
            try:
                response_data = response.json()
            except:
                self._report(f"SUBDL Debug - Raw Response: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            if 'status' in data:
                return data['status']
            elif 'ok' in data:
                return data['ok']
                
            self._report(f"Failed to complete subtitle upload to subdl: Unexpected response format")
            return False
            
        except requests.exceptions.RequestException as e:
            self._report(f"Failed to complete subtitle upload to subdl: {str(e)}")
            self._report(f"SUBDL Debug - Error Details: {traceback.format_exc()}")
            return False

    def upload_subtitle(self, subtitle_file, tmdb_id, season, releases, language_id, 
                   comment="", framerate="23.976", episode_from=None, episode_to=None):
        """Upload subtitle with specific language code"""
        if language_id not in self.LANGUAGES:
            self._report(f"Invalid language code: {language_id}")
            return False

        try:
            if not self.token:
                raise Exception('Missing subdl token in database')
            print(f"got subdl token: {self.token}")

            # Step 1: Get NID
            n_id = self.get_nid()
            if not n_id:
                raise Exception('Failed to get NID')
            print(f"fetched subdl nid: {n_id}")

            # Step 2: Upload subtitle file
            file_n_id = self.upload_subtitle_file(subtitle_file)
            if not file_n_id:
                raise Exception('Failed to upload subtitle file')
            print(f"uploaded subtitle file: {file_n_id}")

            # Step 3: Complete upload with metadata
            upload_data = {
                'file_n_id': file_n_id,
                'tmdb_id': tmdb_id,
                'name': Path(subtitle_file).stem,
                'release': releases,
                'season': season,
                'n_id': n_id,
                'language': language_id,
                'comment': comment,
                'framerate': framerate
            }
            
            success = self.complete_upload(upload_data)
            if not success:
                raise Exception('Failed to complete subtitle upload')
                
            self._report(f"SUBDL: Successfully uploaded subtitle {Path(subtitle_file).name}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error uploading subtitle to subdl: {error_msg}")
            self._report(f"SUBDL: Upload failed - {error_msg}")
            return False

    def _report(self, message):
        """Helper method to handle error reporting"""
        print(message)  # For now just print, can be enhanced later

    def get_language_id(self, lang_code):
        """Convert ISO language code to Subdl language ID"""
        return self.LANGUAGE_MAP.get(lang_code.lower())