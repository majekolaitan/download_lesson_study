import os
import requests
from datetime import datetime, timedelta
import re
import glob
import yt_dlp
from googleapiclient.discovery import build  # Google API Client for YouTube API
from googleapiclient.errors import HttpError

# Set environment to either 'test' or 'production'
environment = 'production'  # Change to 'production' when using the real YouTube API

# Use environment variable for YouTube API key
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # Fetch API key from environment variable

# YouTube API service details
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Channel IDs and query formats
CHANNEL_IDS = {
    '3abn': {'id': 'UCw_AthKfwqB3XYpboTFZFmg', 'query_format': '{lesson_title} | Sabbath School Panel by 3ABN - Lesson {lesson_number} Q{quarter} {year}'},
    'itiswritten': {'id': 'UCtWyoUrGPAkZgnp2486Ir4w', 'query_format': 'Sabbath School - {year} Q{quarter} Lesson {lesson_number}: {lesson_title}'},
    'hopess': {'id': 'UCm34NbuHzE9t9hHutOxwIOA', 'query_format': 'Lesson {lesson_number}: {lesson_title}'},
    'claudiocarneiro': {'id': 'UCvJRu-jirSkv6yuxakirENg', 'query_format': '{year} Q{quarter} Lesson {lesson_number} – {lesson_title} – Audio by Percy Harrold'},
    'HopeLives365': {'id': 'UCOuDMda3jxj-g_iI1P2d2zw', 'query_format': 'Sabbath School with Mark Finley | Lesson {lesson_number} — Q{quarter} – {year}'},
    'egwhiteaudio': {'id': 'UCPS3A-60tKmKTCKWZMT9upA', 'query_format': '{year} Q{quarter} Lesson {lesson_number} – EGW Notes – {lesson_title}'},
}

# In test environment, map each channel to a predefined URL
TEST_URLS = {
    '3abn': 'https://www.youtube.com/watch?v=-eZepvX6UVw',
    'itiswritten': 'https://www.youtube.com/watch?v=t_VM__8B1vk',
    'hopess': 'https://www.youtube.com/watch?v=K83lvzmelOo',
    'claudiocarneiro': 'https://www.youtube.com/watch?v=qJSuxbIi3Bg',
    'HopeLives365': 'https://www.youtube.com/watch?v=Ivpr9P-OA4A',
    'egwhiteaudio': 'https://www.youtube.com/watch?v=kOQosyJhrIE',
}

# Check if the API key is set
if not YOUTUBE_API_KEY:
    raise EnvironmentError("YouTube API key not found in environment variables. Please set 'YOUTUBE_API_KEY'.")

# Initialize YouTube API client only if in production
if environment == 'production':
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)


def search_videos_on_youtube(query, channel_name, channel_id, max_results=1):
    """
    Search YouTube for videos using the YouTube Data API v3 if in 'production', or simulate search in 'test'.
    """
    if environment == 'production':
        try:
            # Perform the YouTube search
            search_response = youtube.search().list(
                q=query,
                part='snippet',
                maxResults=max_results,
                channelId=channel_id,
                type='video',
                order='date'
            ).execute()

            # Check if there are videos returned
            videos = search_response.get('items', [])
            if not videos or 'videoId' not in videos[0].get('id', {}):
                print(f"No results found for query: {query}")
                return None

            # Extract and return the first video's URL
            video_id = videos[0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"

        except HttpError as e:
            print(f"An HTTP error occurred: {e.content}")
            return None
        except KeyError as e:
            print(f"Expected key missing in the response: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
    else:
        # Simulate search in 'test' environment using predefined URLs
        video_url = TEST_URLS.get(channel_name)
        if video_url:
            print(f"Simulated URL found for {channel_name}: {video_url}")
            return video_url
        else:
            print(f"No test URL found for {channel_name}. Returning None.")
            return None

        
# Function to search YouTube for the current lesson title
def get_lesson_title(lesson_number, quarter, year):
    """
    Search YouTube for the title of the current lesson and extract it from the first result.
    """
    query = f"Sabbath School Panel by 3ABN - Lesson {lesson_number} Q{quarter} {year}"
    ydl_opts = {
        'extract_flat': True,  # Use flat extraction for faster search
        'quiet': True,         # Reduce verbosity
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch:{query}", download=False)

            # Check if any results were found
            if 'entries' not in search_results or not search_results['entries']:
                print(f"No results found for: {query}")
                return None

            # Get the first result's title
            video_title = search_results['entries'][0]['title']
            print(f"Found video title: {video_title}")

            # Extract the lesson title (before "|")
            if "|" in video_title:
                lesson_title = video_title.split("|")[0].strip()
                lesson_title = lesson_title.strip('"').strip('“').strip('”').strip("'")
                print(f"Extracted lesson title: {lesson_title}")
                return lesson_title
            else:
                print("No '|' found in the title, using the full title.")
                return video_title.strip()

    except Exception as e:
        print(f"An error occurred while fetching the lesson title: {e}")
        return None

def search_and_save_urls(lesson_number, quarter, year, url_file='urls.txt'):
    """
    Search for videos based on queries using the YouTube Data API and save the first result's URL to a file.
    """
    # Delete the existing file if it exists
    if os.path.exists(url_file):
        print(f"Deleting existing {url_file}...")
        os.remove(url_file)

    # Search and extract the title for the current lesson
    lesson_title = get_lesson_title(lesson_number, quarter, year)

    if not lesson_title:
        print("Failed to fetch a valid lesson title. Skipping search.")
        return

    # Loop through the predefined channels
    for channel_name, channel_data in CHANNEL_IDS.items():
        # Get the channel-specific query format
        query_format = channel_data['query_format']
        
        # Construct the search query using the channel-specific format
        query = query_format.format(lesson_number=lesson_number, quarter=quarter, year=year, lesson_title=lesson_title)
        channel_id = channel_data['id']

        # Search YouTube for the video
        print(f"Searching {channel_name} for: {query}")
        video_url = search_videos_on_youtube(query, channel_name, channel_id)

        if video_url:
            print(f"Found video URL: {video_url}")
            with open(url_file, 'a') as f:
                f.write(f"{video_url}\n")

def get_quarter_and_week(date):
    # Get the month of the given date
    month = date.month

    # Determine which quarter the month falls in
    if 1 <= month <= 3:
        quarter_start_month = 1
        quarter = 1
    elif 4 <= month <= 6:
        quarter_start_month = 4
        quarter = 2
    elif 7 <= month <= 9:
        quarter_start_month = 7
        quarter = 3
    else:
        quarter_start_month = 10
        quarter = 4

    # Find the start of the quarter (first day of the quarter)
    quarter_start = datetime(date.year, quarter_start_month, 1)

    # Adjust the quarter start to the previous Saturday (or same day if it's Saturday)
    # In Python, weekday(): Monday is 0 and Sunday is 6. So Saturday is 5.
    quarter_start_weekday = quarter_start.weekday()
    days_since_saturday = (quarter_start_weekday - 5) % 7
    week_start_date = quarter_start - timedelta(days=days_since_saturday)

    # Calculate the difference in days between the date and the adjusted week start date
    day_difference = (date - week_start_date).days

    # Calculate the week number of the quarter, weeks start on Saturday
    week_of_quarter = (day_difference // 7) + 1

    return quarter, week_of_quarter

def download_audio_from_urls(url_file='urls.txt', downloaded_file='downloaded.txt'):
    """
    Download audio from the URLs saved in a file and track downloaded URLs.
    """
    if not os.path.exists(downloaded_file):
        with open(downloaded_file, 'w') as f:
            pass

    with open(downloaded_file, 'r') as f:
        downloaded_urls = set(f.read().splitlines())

    ydl_opts = {
        'format': '139/140',  # Audio-only formats
        'quiet': False
    }

    with open(url_file, 'r') as f:
        urls = f.read().splitlines()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            if url not in downloaded_urls:
                try:
                    print(f"Downloading audio from: {url}")
                    ydl.download([url])

                    with open(downloaded_file, 'a') as df:
                        df.write(f"{url}\n")
                except Exception as e:
                    print(f"Error downloading {url}: {e}")
            else:
                print(f"Already downloaded: {url}")


def compare_and_cleanup_lesson_files(current_year, current_quarter, current_lesson_number):
    """
    Compare current lesson with existing files and delete all .mp3, .m4a files, and specific text files
    if the current lesson is greater.
    """
    # Search for files with pattern YYYY QX Lesson XX
    lesson_pattern = r"(\d{4})\s*Q(\d)\s*Lesson\s*(\d+)"
    lesson_files = glob.glob(f"*Lesson*.mp3") + glob.glob(f"*Lesson*.m4a")

    if not lesson_files:
        print("No previous lesson files found.")
        return

    for file_name in lesson_files:
        # Extract year, quarter, and lesson number from the file name using refined regex
        match = re.search(lesson_pattern, file_name)
        if match:
            file_year = int(match.group(1))
            file_quarter = int(match.group(2))
            file_lesson_number = int(match.group(3))

            # Compare with the current lesson
            if (file_year < current_year or
                (file_year == current_year and file_quarter < current_quarter) or
                (file_year == current_year and file_quarter == current_quarter and file_lesson_number < current_lesson_number)):

                print(f"Current lesson is greater than {file_name}. Deleting all .mp3, .m4a, 'downloaded.txt', and 'urls.txt' files.")
                delete_audio_files()
                break
            else:
                print(f"{file_name} is up-to-date. Continuing execution.")
        else:
            print(f"File {file_name} does not match the lesson pattern.")

def delete_audio_files():
    """
    Delete all .mp3, .m4a files, and 'downloaded.txt' and 'urls.txt' in the current directory.
    """
    audio_files = glob.glob("*.mp3") + glob.glob("*.m4a")
    for audio_file in audio_files:
        try:
            os.remove(audio_file)
            print(f"Deleted: {audio_file}")
        except OSError as e:
            print(f"Error deleting {audio_file}: {e}")

    # Delete 'downloaded.txt' and 'urls.txt' if they exist
    for file_name in ['downloaded.txt', 'urls.txt']:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                print(f"Deleted: {file_name}")
            except OSError as e:
                print(f"Error deleting {file_name}: {e}")

# Function to download daily lesson audio files
def download_daily_lesson_audio_files():
    """
    Download daily lesson audio files from a pre-defined URL format based on the last Saturday.
    """
    today = datetime.today()
    
    # Find the last Saturday
    last_saturday = today - timedelta(days=(today.weekday() + 2) % 7)

    # Loop from last Saturday to Friday of the current week (last Saturday + 6 days)
    for i in range(7):
        download_date = last_saturday + timedelta(days=i)
        formatted_date = download_date.strftime('%Y-%m-%d')
        url = f"https://d7dlhz1yjc01y.cloudfront.net/audio/en/lessons/{formatted_date}.mp3"
        
        # Check if the file is available by making a HEAD request
        try:
            head_response = requests.head(url, timeout=10)
            if head_response.status_code == 200:
                # Check if the file is already downloaded before calling download
                if not os.path.exists(formatted_date + '.mp3'):
                    download_file(url)
                else:
                    print(f"File {formatted_date}.mp3 already exists. Skipping download.")
            else:
                print(f"File not found for {formatted_date}. Skipping.")
        except requests.exceptions.RequestException as e:
            print(f"Error checking availability for {url}: {e}")

def download_file(url):
    """
    Helper function to download a file from a given URL.
    Skips downloading if the file already exists.
    """
    local_filename = url.split('/')[-1]

    # Check if the file already exists
    if os.path.exists(local_filename):
        print(f"File {local_filename} already exists. Skipping download.")
        return

    try:
        print(f"Downloading {url}")
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded: {local_filename}")
    except requests.exceptions.Timeout:
        print(f"Request timed out: {url}")
    except requests.exceptions.ConnectionError:
        print(f"Connection error occurred for: {url}")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")


# Main logic
if __name__ == "__main__":

    today = datetime.today()
    current_quarter, current_lesson_number = get_quarter_and_week(today)
    current_year = today.year

    print(f"Current Year: {current_year}, Quarter: {current_quarter}, Lesson: {current_lesson_number}")

    # Step 1: Compare and clean up old lesson files
    compare_and_cleanup_lesson_files(current_year, current_quarter, current_lesson_number)

    # Step 2: Search and save URLs
    search_and_save_urls(lesson_number=current_lesson_number, quarter=current_quarter, year=current_year)

    # Step 3: Download audio from the saved URLs
    download_audio_from_urls(url_file='urls.txt', downloaded_file='downloaded.txt')

    # Step 4: Download weekly lesson audio files
    download_daily_lesson_audio_files()
