import os
import cv2
import time
import yt_dlp
import torch
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from moviepy.video.io.VideoFileClip import VideoFileClip
from transformers import CLIPProcessor, CLIPModel
from ultralytics import YOLO
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

if not API_KEY:
    raise ValueError("❌ API_KEY is missing. Make sure you have a .env file with YOUTUBE_API_KEY set.")

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Ładowanie modeli AI
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
yolo_model = YOLO("yolov8n.pt")

def get_random_trending_video(region_code="PL"):
    """ Pobiera losowe popularne wideo na YouTube """
    try:
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
        request = youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=10
        )
        response = request.execute()
        if not response.get("items"):
            return None
        video = response["items"][3]
        return video["snippet"]["title"], f"https://www.youtube.com/watch?v={video['id']}"
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return None

def download_video(video_url, output_path="video.mp4"):
    """ Pobiera wideo z YouTube """
    ydl_opts = {'format': 'mp4', 'outtmpl': output_path, 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Video unavailable: {e}")

def extract_frames(video_path, interval=10, output_folder="frames"):
    """ Ekstrahuje klatki co X sekund """
    os.makedirs(output_folder, exist_ok=True)
    clip = VideoFileClip(video_path)
    frame_paths = []
    
    for t in range(0, int(clip.duration), interval):
        frame = clip.get_frame(t)
        frame_path = os.path.join(output_folder, f"frame_{t}.jpg")
        cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        frame_paths.append((t, frame_path))
    
    clip.close()
    return frame_paths

def detect_objects(frame_path):
    """ Wykrywa obiekty w klatce """
    frame = cv2.imread(frame_path)
    results = yolo_model(frame)
    return [results[0].names[int(c)] for c in results[0].boxes.cls]

def describe_frame_gemini(frame_path):
    """ Generuje opis sceny za pomocą API Gemini """
    frame = cv2.imread(frame_path)
    _, encoded_image = cv2.imencode('.jpg', frame)
    image_bytes = encoded_image.tobytes()
    
    response = genai.chat().send_message([
        {"type": "image", "data": image_bytes},
        {"type": "text", "data": "Co znajduje się na tym obrazie? Opisz to szczegółowo."}
    ])
    return response.text

def generate_highlights(frames):
    """ Wybiera najbardziej interesujące momenty """
    highlights = []
    
    for timestamp, frame_path in frames:
        objects = detect_objects(frame_path)
        description = describe_frame_gemini(frame_path)
        
        # Jeśli klatka zawiera dynamiczne elementy, dodaj do highlightów
        if any(obj in objects for obj in ["person", "car", "ball", "explosion", "crowd"]):
            highlights.append(f"{timestamp}s: {description} (Obiekty: {', '.join(objects)})")
    
    return highlights

def save_highlights_to_file(highlights, output_file="highlights.txt"):
    """ Zapisuje highlighty do pliku """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(highlights))

def main():
    print("🔍 Fetching a random trending video...")
    video_data = get_random_trending_video()
    
    if not video_data:
        print("⚠ No trending videos found. Exiting...")
        return
    
    title, url = video_data
    print(f"\n🎬 Processing video: {title}")
    video_path = "video.mp4"

    print("⬇ Downloading video...")
    download_video(url, video_path)

    if not os.path.exists(video_path):
        print(f"⚠ Skipping {title}, download failed.")
        return

    print("📸 Extracting frames...")
    frames = extract_frames(video_path)

    print("📝 Generating highlights...")
    highlights = generate_highlights(frames)

    print("💾 Saving highlights...")
    save_highlights_to_file(highlights)

    print("✅ Done! Highlights saved in 'highlights.txt'.")
    os.remove(video_path)

if __name__ == "__main__":
    main()
