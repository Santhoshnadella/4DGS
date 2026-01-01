import random
import glob
from pathlib import Path
import cv2

def create_point_cloud(frames_dir, output_path, num_points=5000):
    """Create a random initialized point cloud based on frame colors."""
    frames_dir = Path(frames_dir)
    frame_files = sorted(list(frames_dir.glob('frame_*.jpg')))
    
    if not frame_files:
        return False
        
    first_frame = cv2.imread(str(frame_files[0]))
    height, width = first_frame.shape[:2]
    
    points = []
    for _ in range(num_points):
        x = random.uniform(-2, 2)
        y = random.uniform(-1, 1)
        z = random.uniform(1, 4)
        
        frame_idx = random.randint(0, len(frame_files)-1)
        frame = cv2.imread(str(frame_files[frame_idx]))
        
        px = random.randint(0, width-1)
        py = random.randint(0, height-1)
        color = frame[py, px][::-1] # BGR to RGB
        
        points.append([x, y, z, color[0]/255.0, color[1]/255.0, color[2]/255.0])
        
    with open(output_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        
        for p in points:
            f.write(f"{p[0]} {p[1]} {p[2]} {int(p[3]*255)} {int(p[4]*255)} {int(p[5]*255)}\n")
            
    return True
