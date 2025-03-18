import os
import cv2
import time
import yt_dlp
from googleapiclient.discovery import build
from moviepy.video.io.VideoFileClip import VideoFileClip
from scenedetect import VideoManager, SceneManager, open_video
from scenedetect.detectors import ContentDetector

API_KEY = ".env"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def get_trending_videos(region_code="PL", max_results=2):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    request = youtube.videos().list(
        part="snippet",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    )
    response = request.execute()
    videos = []
    
    for item in response.get("items", []):
        video_id = item["id"]
        title = item["snippet"]["title"]
        url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append((title, url))
    
    return videos

def download_video(video_url, output_path="video.mp4"):
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': output_path,
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def detect_scenes(video_path):
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0))
    scene_manager.detect_scenes(video)
    
    return scene_manager.get_scene_list()

def capture_screenshots(video_path, scenes, output_folder="screenshots"):
    os.makedirs(output_folder, exist_ok=True)
    clip = VideoFileClip(video_path)
    
    for i, (start, end) in enumerate(scenes[:5]):
        frame_time = (start.get_seconds() + end.get_seconds()) / 2
        frame = clip.get_frame(frame_time)
        img_path = os.path.join(output_folder, f"scene_{i + 1}.jpg")
        cv2.imwrite(img_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    clip.close()

def main():
    print("Get trending video...")
    trending_videos = get_trending_videos("US", 2)
    
    for title, url in trending_videos:
        print(f"\n🎬 Video processing...: {title}")
        video_path = "video.mp4"
        print("⬇ Video downloading...")
        download_video(url, video_path)
        print("🔎 Analysis bright scenes...")
        scenes = detect_scenes(video_path)
        print("📸 Screenshot creating...")
        capture_screenshots(video_path, scenes)
        print(f"✅ Completed! Screenshots saved at 'screenshots'.")
        os.remove(video_path)
    
    print("\n✅ All videos are already added!")

if __name__ == "__main__":
    while True:
        main()
        print("\n⏳ Wait 30 min before update...")
        time.sleep(1800)
