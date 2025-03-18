import os
import re
import json
import time
import requests
import cv2
import yt_dlp
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy import concatenate_videoclips
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("❌ API_KEY is missing. Make sure you have a .env file with YOUTUBE_API_KEY set.")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_trending_videos(region_code="PL", max_results=2):
    """ Pobiera listę popularnych filmów na YouTube """
    try:
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
        request = youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results
        )
        response = request.execute()
        videos = [(item["snippet"]["title"], f"https://www.youtube.com/watch?v={item['id']}") 
                  for item in response.get("items", [])]
        return videos
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return []


def get_most_replayed(video_id):
    """ Pobiera timestampy najczęściej oglądanych momentów na YouTube """
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("❌ Błąd pobierania strony!")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    
    script_tags = soup.find_all("script")
    for script in script_tags:
        if "ytInitialData" in script.text:
            json_text = re.search(r"var ytInitialData = ({.*?});", script.text)
            if json_text:
                data = json.loads(json_text.group(1))
                
                try:
                    markers = data['frameworkUpdates']['entityBatchUpdate']['mutations'][0]['payload']['macroMarkersListEntity']['markersList']['markers']
                    
                    timestamps = [int(marker["startMillis"]) / 1000 for marker in markers]  # Konwersja ms → sekundy
                    return timestamps
                
                except KeyError:
                    print("⚠ Brak danych o 'Most Replayed' w tym filmie.")
                    return None

    print("❌ Nie znaleziono odpowiednich danych!")
    return None


def download_video(video_url, output_path="video.mp4"):
    """ Pobiera wideo z YouTube """
    ydl_opts = {'format': 'mp4', 'outtmpl': output_path, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Video unavailable: {e}")


def extract_top_moments(video_path, timestamps, duration=10, output_folder="output_clips"):
    """ Wycinanie najczęściej oglądanych momentów """
    os.makedirs(output_folder, exist_ok=True)
    clip = VideoFileClip(video_path)
    extracted_clips = []

    for i, start_time in enumerate(timestamps[:5]):  # Maksymalnie 5 najlepszych fragmentów
        end_time = min(start_time + duration, clip.duration)
        subclip = clip.subclip(start_time, end_time)
        output_file = os.path.join(output_folder, f"clip_{i+1}.mp4")
        subclip.write_videofile(output_file, codec="libx264")
        extracted_clips.append(subclip)

    clip.close()
    return extracted_clips


def merge_clips(clips, output_path="merged_video.mp4"):
    """ Łączy wycięte fragmenty w jeden film """
    if not clips:
        print("⚠ Brak klipów do połączenia!")
        return
    
    final_video = concatenate_videoclips(clips)
    final_video.write_videofile(output_path, codec="libx264")
    print(f"✅ Połączony film zapisany jako: {output_path}")


def main():
    print("🔍 Pobieranie popularnych filmów...")
    trending_videos = get_trending_videos("US", 2)
    
    if not trending_videos:
        print("⚠ Nie znaleziono popularnych filmów. Zamykanie...")
        return

    for title, url in trending_videos:
        print(f"\n🎬 Przetwarzanie filmu: {title}")
        video_id = url.split("v=")[1]
        video_path = "video.mp4"

        print("⬇ Pobieranie filmu...")
        download_video(url, video_path)

        if not os.path.exists(video_path):
            print(f"⚠ Pominięto {title}, pobieranie nie powiodło się.")
            continue

        print("🔥 Pobieranie najczęściej oglądanych momentów...")
        timestamps = get_most_replayed(video_id)
        if not timestamps:
            print("⚠ Brak danych 'Most Replayed', pomijanie filmu.")
            continue

        print("✂ Wycinanie najlepszych momentów...")
        extracted_clips = extract_top_moments(video_path, timestamps)

        print("🎬 Łączenie klipów w jeden film...")
        merge_clips(extracted_clips)

        print(f"✅ Zakończono przetwarzanie {title}")
        os.remove(video_path)

    print("\n✅ Wszystkie filmy przetworzone!")


if __name__ == "__main__":
    while True:
        main()
        print("\n⏳ Czekam 30 minut przed kolejną aktualizacją...")
        time.sleep(1800)
