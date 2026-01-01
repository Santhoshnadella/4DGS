
import os
import shutil
import glob
import subprocess
import cv2
import ffmpeg
import numpy as np
import math
from pathlib import Path
import logging

def extract_frames(video_path, output_dir, fps=2, max_dim=1280):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get video properties
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        duration = float(video_stream['duration'])
        total_frames = int(video_stream['nb_frames'])
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg probe failed: {e.stderr.decode() if e.stderr else str(e)}")
        # Fallback if probe fails? Or just re-raise
        raise

    frames_to_extract = min(int(duration * fps), total_frames)
    
    try:
        (
            ffmpeg
            .input(video_path)
            .filter('fps', fps=fps)
            .output(str(output_dir / 'frame_%04d.jpg'), vframes=frames_to_extract)
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg extraction failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise

    frame_files = sorted(list(output_dir.glob('frame_*.jpg')))
    
    # Resize
    for frame_path in frame_files:
        img = cv2.imread(str(frame_path))
        if img is None: continue
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(img, (new_w, new_h))
            cv2.imwrite(str(frame_path), resized)
            
    return len(frame_files), str(output_dir)

def run_colmap(frames_dir, output_dir):
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "database.db"

    colmap_bin = "colmap" 
    
    commands = [
        [colmap_bin, "feature_extractor", "--database_path", str(database_path), "--image_path", str(frames_dir), "--ImageReader.single_camera", "1", "--ImageReader.camera_model", "PINHOLE"],
        [colmap_bin, "exhaustive_matcher", "--database_path", str(database_path)],
        [colmap_bin, "mapper", "--database_path", str(database_path), "--image_path", str(frames_dir), "--output_path", str(sparse_dir)],
        [colmap_bin, "model_converter", "--input_path", str(sparse_dir / "0"), "--output_path", str(sparse_dir / "0"), "--output_type", "TXT"]
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            return False

    return (sparse_dir / "0" / "images.txt").exists()

def generate_placeholder_poses(frame_count, output_dir, img_width=1280, img_height=720):
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    
    focal = max(img_width, img_height) * 1.2
    
    with open(sparse_dir / "cameras.txt", "w") as f:
        f.write("# Camera list\n# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(f"1 PINHOLE {img_width} {img_height} {focal} {focal} {img_width/2} {img_height/2}\n")
    
    with open(sparse_dir / "images.txt", "w") as f:
        f.write("# Image list\n# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        radius = 3.0
        for i in range(frame_count):
            angle = 2 * math.pi * i / frame_count
            x, z = radius * math.cos(angle), radius * math.sin(angle)
            # Placeholder lookat logic
            f.write(f"{i+1} 1 0 0 0 {x} 0 {z} 1 frame_{i+1:04d}.jpg\n\n")
            
    with open(sparse_dir / "points3D.txt", "w") as f:
        f.write("# 3D point list\n")

def create_point_cloud(frames_dir, output_path, num_points=5000):
    frames_dir = Path(frames_dir)
    frame_files = sorted(list(frames_dir.glob('frame_*.jpg')))
    if not frame_files: return
    
    points = []
    for _ in range(num_points):
        points.append([np.random.uniform(-2,2), np.random.uniform(-1,1), np.random.uniform(1,4), 
                       np.random.randint(0,255), np.random.randint(0,255), np.random.randint(0,255)])
        
    with open(output_path, 'w') as f:
        f.write(f"ply\nformat ascii 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
        for p in points:
            f.write(f"{p[0]} {p[1]} {p[2]} {int(p[3])} {int(p[4])} {int(p[5])}\n")
