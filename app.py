
import sys
import os
import gradio as gr
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime
import logging
import plotly.graph_objects as go
import numpy as np

# Adjust path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.preprocessing import extract_frames, run_colmap, generate_placeholder_poses
from src.training import train_model, create_config_file, TrainingMonitor
from src.rendering import render_video
from src.utils import create_point_cloud

logging.basicConfig(level=logging.INFO)

def visualize_point_cloud(ply_path):
    if not os.path.exists(ply_path):
        return None
    try:
        # Basic PLY reader
        with open(ply_path, 'r') as f:
            header = True
            points = []
            colors = []
            for line in f:
                if "end_header" in line:
                    header = False
                    continue
                if header: continue
                
                parts = line.strip().split()
                if len(parts) >= 6:
                    points.append([float(x) for x in parts[0:3]])
                    colors.append(f"rgb({parts[3]},{parts[4]},{parts[5]})")
                    
        points = np.array(points)
        # Downsample for UI
        if len(points) > 10000:
            indices = np.random.choice(len(points), 10000, replace=False)
            points = points[indices]
            colors = [colors[i] for i in indices]
            
        fig = go.Figure(data=[go.Scatter3d(
            x=points[:,0], y=points[:,1], z=points[:,2],
            mode='markers',
            marker=dict(size=2, color=colors)
        )])
        fig.update_layout(
             scene=dict(bgcolor='#0b0f19'),
             paper_bgcolor='#0b0f19',
             margin=dict(l=0, r=0, b=0, t=0)
        )
        return fig
    except Exception as e:
        logging.error(f"Viz error: {e}")
        return None

def main_process(video_path, fps, iterations, use_colmap, progress=gr.Progress()):
    if not video_path:
        return None, None, "No video provided.", None
        
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path("workspaces") / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    logs = []
    def log(msg):
        entry = f"[{datetime.now().time()}] {msg}"
        logs.append(entry)
        return "\n".join(logs)
    
    # 1. Extraction
    progress(0.1, desc="Extracting Frames")
    frames_dir = session_dir / "frames"
    count, _ = extract_frames(video_path, frames_dir, fps)
    yield None, None, log(f"Extracted {count} frames"), None
    
    # 2. Structure
    progress(0.2, desc="Structure from Motion")
    if use_colmap:
        res = run_colmap(frames_dir, session_dir)
        if not res:
            log("COLMAP failed, using placeholder")
            generate_placeholder_poses(count, session_dir)
    else:
        generate_placeholder_poses(count, session_dir)
        
    ply_path = session_dir / "points3D.ply"
    create_point_cloud(frames_dir, ply_path)
    fig = visualize_point_cloud(str(ply_path))
    yield None, fig, log("Structure computed"), None
    
    # 3. Training
    progress(0.4, desc="Training (4DGS)")
    config = {"iterations": iterations}
    config_path = create_config_file(session_dir, config)
    
    try:
        model_path = train_model(session_dir, config_path, iterations=iterations)
        yield None, fig, log("Training Complete"), None
    except Exception as e:
        yield None, fig, log(f"Training Error: {e}"), None
        return # Stop if training fails
        
    # 4. Rendering
    progress(0.9, desc="Rendering Video")
    video_path = session_dir / "output.mp4"
    final_video = render_video(model_path, video_path)
    
    zip_path = shutil.make_archive(str(session_dir/"export"), 'zip', session_dir)
    
    yield final_video, fig, log("Process Complete"), zip_path

def create_ui():
    css = """
    body { background-color: #0b0f19; color: #fff; }
    .gradio-container { background-color: #0b0f19; }
    #title { 
        background: linear-gradient(90deg, #4f46e5, #ec4899); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-weight: 800; font-size: 2.5em; 
        text-align: center;
        margin-bottom: 20px;
    }
    .primary-btn { background: #4f46e5; border-radius: 8px; color: white; font-weight: bold; }
    .panel { background: #1f2937; border-radius: 12px; padding: 15px; border: 1px solid #374151; }
    """
    
    with gr.Blocks(css=css, theme=gr.themes.Soft(), title="4DGS Studio") as app:
        gr.Markdown("# 4DGS Studio Production Environment", elem_id="title")
        
        with gr.Row():
            with gr.Column(scale=1, elem_classes="panel"):
                video_in = gr.Video(label="Input Video")
                fps = gr.Slider(1, 10, value=2, step=1, label="FPS Extraction")
                iters = gr.Slider(500, 10000, value=3000, step=500, label="Training Iterations")
                colmap = gr.Checkbox(label="Use COLMAP", value=False)
                run_btn = gr.Button("Start Processing", elem_classes="primary-btn")
                
                dl = gr.File(label="Export Workspace")
                
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.TabItem("4D View"):
                        video_out = gr.Video(label="Rendered 4D Video")
                    with gr.TabItem("3D Structure"):
                        plot_3d = gr.Plot(label="Point Cloud")
                    with gr.TabItem("Logs"):
                        logs = gr.Textbox(label="System Logs", lines=10)
                        
        run_btn.click(
            main_process,
            inputs=[video_in, fps, iters, colmap],
            outputs=[video_out, plot_3d, logs, dl]
        )
        
    return app

if __name__ == "__main__":
    ui = create_ui()
    ui.launch(server_name="127.0.0.1", port=7860, share=True)
