import os
import cv2
import time
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from moviepy.video.io.VideoFileClip import VideoFileClip
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
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

def download_video(video_url, output_path="video.mp4"):
    """ Pobiera wideo z YouTube """
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': output_path,
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Video unavailable: {e}")

def detect_scenes(video_path):
    """ Wykrywa sceny w wideo """
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0))
    scene_manager.detect_scenes(video)
    return scene_manager.get_scene_list()

def capture_screenshots(video_path, scenes, output_folder="screenshots"):
    """ Tworzy zrzuty ekranu dla wykrytych scen """
    if not scenes:
        print("⚠ No scenes detected. Skipping screenshots.")
        return

    os.makedirs(output_folder, exist_ok=True)
    clip = VideoFileClip(video_path)
    
    for i, (start, end) in enumerate(scenes[:5]):
        frame_time = (start.get_seconds() + end.get_seconds()) / 2
        frame = clip.get_frame(frame_time)
        img_path = os.path.join(output_folder, f"scene_{i + 1}.jpg")
        cv2.imwrite(img_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    clip.close()

def main():
    print("🔍 Fetching trending videos...")
    trending_videos = get_trending_videos("US", 2)
    
    if not trending_videos:
        print("⚠ No trending videos found. Exiting...")
        return

    for title, url in trending_videos:
        print(f"\n🎬 Processing video: {title}")
        video_path = "video.mp4"

        print("⬇ Downloading video...")
        download_video(url, video_path)

        if not os.path.exists(video_path):
            print(f"⚠ Skipping {title}, download failed.")
            continue

        print("🔎 Analyzing scenes...")
        scenes = detect_scenes(video_path)

        print("📸 Capturing screenshots...")
        capture_screenshots(video_path, scenes)

        print(f"✅ Done! Screenshots saved in 'screenshots' folder.")
        os.remove(video_path)

    print("\n✅ All videos processed!")

if __name__ == "__main__":
    while True:
        main()
        print("\n⏳ Waiting 30 minutes before next update...")
        time.sleep(1800)
