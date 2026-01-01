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

logger = logging.getLogger(__name__)

def extract_frames(video_path, output_dir, fps=2, max_dim=1280):
    """Extract frames from video at specified FPS."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get video properties
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            raise ValueError("No video stream found in file.")
            
        duration = float(video_stream['duration'])
        total_frames = int(video_stream['nb_frames'])
        logger.info(f"Video duration: {duration}s, Total frames: {total_frames}")
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg probe failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise

    # Calculate frames to extract
    frames_to_extract = min(int(duration * fps), total_frames)
    
    # Extract
    try:
        (
            ffmpeg
            .input(video_path)
            .filter('fps', fps=fps)
            .output(str(output_dir / 'frame_%04d.jpg'), vframes=frames_to_extract)
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg extraction failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise

    frame_files = sorted(list(output_dir.glob('frame_*.jpg')))
    frame_count = len(frame_files)
    
    # Resize
    for frame_path in frame_files:
        img = cv2.imread(str(frame_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(img, (new_w, new_h))
            cv2.imwrite(str(frame_path), resized)
            
    return frame_count, str(output_dir)

def run_colmap(frames_dir, output_dir):
    """Run COLMAP for camera pose estimation."""
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "database.db"

    colmap_bin = "colmap" # Assumes colmap is in PATH
    
    commands = [
        # Feature extraction
        [
            colmap_bin, "feature_extractor",
            "--database_path", str(database_path),
            "--image_path", str(frames_dir),
            "--ImageReader.single_camera", "1",
            "--ImageReader.camera_model", "PINHOLE",
            "--SiftExtraction.use_gpu", "1"
        ],
        # Feature matching
        [
            colmap_bin, "exhaustive_matcher",
            "--database_path", str(database_path),
            "--SiftMatching.use_gpu", "1"
        ],
        # Sparse reconstruction
        [
            colmap_bin, "mapper",
            "--database_path", str(database_path),
            "--image_path", str(frames_dir),
            "--output_path", str(sparse_dir)
        ]
    ]

    for cmd in commands:
        logger.info(f"Running COLMAP command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"COLMAP failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False

    # Bundle adjustment & Conversion
    sparse_reconstruction = sparse_dir / "0"
    if sparse_reconstruction.exists():
        try:
            subprocess.run([
                colmap_bin, "bundle_adjuster",
                "--input_path", str(sparse_reconstruction),
                "--output_path", str(sparse_reconstruction)
            ], check=True, capture_output=True)
            
            subprocess.run([
                colmap_bin, "model_converter",
                "--input_path", str(sparse_reconstruction),
                "--output_path", str(sparse_reconstruction),
                "--output_type", "TXT"
            ], check=True, capture_output=True)
            
            return (sparse_reconstruction / "images.txt").exists()
        except subprocess.CalledProcessError as e:
             logger.error(f"COLMAP refinement failed: {e.stderr.decode() if e.stderr else str(e)}")
             return False
             
    return False

def generate_placeholder_poses(frame_count, output_dir, img_width=1280, img_height=720):
    """Generate placeholder circular camera poses."""
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    
    focal_length = max(img_width, img_height) * 1.2
    
    # cameras.txt
    with open(sparse_dir / "cameras.txt", "w") as f:
        f.write("# Camera list\n")
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(f"1 PINHOLE {img_width} {img_height} {focal_length} {focal_length} {img_width/2} {img_height/2}\n")
    
    # images.txt
    with open(sparse_dir / "images.txt", "w") as f:
        f.write("# Image list\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        
        radius = 3.0
        for i in range(frame_count):
            angle = 2 * math.pi * i / frame_count
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            y = 0.0
            
            # Simple look-at implementation
            camera_pos = np.array([x, y, z])
            forward = -camera_pos / np.linalg.norm(camera_pos) # Look at origin
            up = np.array([0, 1, 0])
            right = np.cross(forward, up)
            right /= np.linalg.norm(right)
            up = np.cross(right, forward)
            
            rot_mat = np.column_stack((right, up, -forward))
            
            # Rotmat to Quaternion
            tr = np.trace(rot_mat)
            if tr > 0:
                S = np.sqrt(tr + 1.0) * 2
                qw = 0.25 * S
                qx = (rot_mat[2, 1] - rot_mat[1, 2]) / S
                qy = (rot_mat[0, 2] - rot_mat[2, 0]) / S
                qz = (rot_mat[1, 0] - rot_mat[0, 1]) / S
            elif (rot_mat[0, 0] > rot_mat[1, 1]) and (rot_mat[0, 0] > rot_mat[2, 2]):
                S = np.sqrt(1.0 + rot_mat[0, 0] - rot_mat[1, 1] - rot_mat[2, 2]) * 2
                qw = (rot_mat[2, 1] - rot_mat[1, 2]) / S
                qx = 0.25 * S
                qy = (rot_mat[0, 1] + rot_mat[1, 0]) / S
                qz = (rot_mat[0, 2] + rot_mat[2, 0]) / S
            elif rot_mat[1, 1] > rot_mat[2, 2]:
                S = np.sqrt(1.0 + rot_mat[1, 1] - rot_mat[0, 0] - rot_mat[2, 2]) * 2
                qw = (rot_mat[0, 2] - rot_mat[2, 0]) / S
                qx = (rot_mat[0, 1] + rot_mat[1, 0]) / S
                qy = 0.25 * S
                qz = (rot_mat[1, 2] + rot_mat[2, 1]) / S
            else:
                S = np.sqrt(1.0 + rot_mat[2, 2] - rot_mat[0, 0] - rot_mat[1, 1]) * 2
                qw = (rot_mat[1, 0] - rot_mat[0, 1]) / S
                qx = (rot_mat[0, 2] + rot_mat[2, 0]) / S
                qy = (rot_mat[1, 2] + rot_mat[2, 1]) / S
                qz = 0.25 * S
                
            tvec = -rot_mat.T @ camera_pos
            
            image_name = f"frame_{i+1:04d}.jpg"
            f.write(f"{i+1} {qw} {qx} {qy} {qz} {tvec[0]} {tvec[1]} {tvec[2]} 1 {image_name}\n")
            f.write("\n")
            
    with open(sparse_dir / "points3D.txt", "w") as f:
        f.write("# 3D point list\n")
        f.write("# POINT3D_ID, XYZ, RGB, ERROR, TRACK[]\n")
        
    return str(sparse_dir)
