
import gradio_client.utils
import logging

# --- MONKEY PATCH START ---
# Comprehensively fix boolean schema issues in Gradio Client (Python 3.9 compat)
# The issue arises when 'additionalProperties': False (bool) is encountered.
_original_schema_converter = gradio_client.utils._json_schema_to_python_type

def _patched_json_schema_to_python_type(schema, defs):
    if isinstance(schema, bool):
        # If schema is a boolean (True/False), just return "Any" or "None" 
        # to prevent 'bool' is not iterable type errors further down.
        return "Any"
    return _original_schema_converter(schema, defs)

gradio_client.utils._json_schema_to_python_type = _patched_json_schema_to_python_type
# --- MONKEY PATCH END ---

import gradio as gr
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil
import time
import json
import traceback

# Configure paths
CURRENT_DIR = Path(__file__).parent.absolute()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import local modules
try:
    from preprocessing import extract_frames, run_colmap, generate_placeholder_poses, create_point_cloud
    DEPENDENCIES_OK = True
except ImportError:
    DEPENDENCIES_OK = False
    print("Warning: Local preprocessing modules not found or dependencies missing.")

logging.basicConfig(level=logging.INFO)

def check_system_health():
    health = {
        "ffmpeg": False,
        "colmap": False,
        "cuda_rasterizer": False,
        "simple_knn": False
    }
    
    health["ffmpeg"] = shutil.which("ffmpeg") is not None
    health["colmap"] = shutil.which("colmap") is not None
    
    try:
        import diff_gaussian_rasterization
        health["cuda_rasterizer"] = True
    except ImportError:
        pass
        
    try:
        import simple_knn
        health["simple_knn"] = True
    except ImportError:
        pass
        
    return health

def run_training_subprocess(session_dir, iterations, is_mock=False):
    output_path = session_dir / "output"
    output_path.mkdir(exist_ok=True, parents=True)
    
    if is_mock:
        # SIMULATION MODE
        yield "⚠️ Simulation Mode: Training functionality is being mocked...", 0
        total_steps = 20
        for i in range(total_steps):
            time.sleep(0.1)
            progress = (i + 1) / total_steps
            yield f"Step {i*50}/{iterations}: Optimizing Gaussians... Loss: {0.8 - (i*0.03):.4f}", progress
            
        yield "Simulation Complete. Model 'saved'.", 1.0
        return str(output_path)

    # REAL MODE
    config_path = session_dir / "config.py"
    
    # Pre-process paths to avoid backslash issues in f-strings
    model_path_str = str(output_path).replace('\\', '/')
    source_path_str = str(session_dir).replace('\\', '/')
    
    with open(config_path, "w") as f:
        f.write(f"""
model_path = "{model_path_str}"
source_path = "{source_path_str}"
iterations = {iterations}
min_opacity = 0.005
sh_degree = 3
white_background = False
        """)
    
    cmd = [
        sys.executable, "train.py",
        "--source_path", str(session_dir),
        "--model_path", str(output_path),
        "--iterations", str(iterations),
        "--configs", str(config_path),
        "--quiet" 
    ]
    
    process = subprocess.Popen(
        cmd, 
        cwd=str(CURRENT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            clean_line = line.strip()
            # Heuristic to parse progress
            if "Iteration" in clean_line or "%" in clean_line:
                yield clean_line, None
            else:
                yield clean_line, None
            
    if process.returncode != 0:
        raise RuntimeError(f"Training failed. Check logs.")
        
    return str(output_path)

def main_pipeline(video, fps, iterations, colmap_enabled, mock_mode):
    # Returns 3 values: (Video, Logs, File)
    
    if not video: 
        # Yield 3 values
        yield None, "❌ Error: No video input", None
        return
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = CURRENT_DIR / "workspaces" / f"session_{session_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    logs = [f"Session initialized at {work_dir}"]
    
    # helper for clean yielding
    def packet(v=None, l=None, f=None):
        return v, l if l else "\n".join(logs), f

    yield packet(l="Starting Pipeline...")
    
    try:
        # 1. Extraction
        logs.append("Phase 1: Extraction...")
        frames_dir = work_dir / "frames"
        
        if DEPENDENCIES_OK:
            try:
                count, _ = extract_frames(video, frames_dir, fps)
                logs.append(f"Extracted {count} frames.")
            except Exception as e:
                logs.append(f"⚠️ Extraction failed (FFmpeg missing?): {e}")
                logs.append("Falling back to Mock Extraction.")
                count = 10
                frames_dir.mkdir(exist_ok=True)
        else:
            count = 10
            frames_dir.mkdir()
            logs.append("Mocking frame extraction (libs missing).")
            
        yield packet()

        # 2. Structure
        if DEPENDENCIES_OK:
            if colmap_enabled:
                try:
                    if run_colmap(frames_dir, work_dir):
                        logs.append("COLMAP reconstruction successful.")
                    else:
                        logs.append("COLMAP failed to converge.")
                        generate_placeholder_poses(count, work_dir)
                except Exception as e:
                    logs.append(f"⚠️ COLMAP Error (Binary missing?): {e}")
                    logs.append("Falling back to Placeholder Poses.")
                    generate_placeholder_poses(count, work_dir)
            else:
                generate_placeholder_poses(count, work_dir)
            create_point_cloud(frames_dir, work_dir / "points3D.ply")
        
        yield packet()
        
        # 3. Training
        logs.append(f"Starting training ({iterations} iters)... Mode: {'MOCK' if mock_mode else 'REAL'}")
        
        try:
            for update_msg, prog_val in run_training_subprocess(work_dir, iterations, is_mock=mock_mode):
                if update_msg and ("Step" in update_msg or "Error" in update_msg or "simulation" in update_msg.lower()):
                    logs.append(update_msg)
                    yield packet()
                        
            logs.append("Training Phase Complete.")
        except Exception as e:
            logs.append(f"Training Error: {e}")
            yield packet()
            return

        # 4. Rendering
        logs.append("Rendering visualization...")
        
        final_video = None
        if mock_mode:
            logs.append("Mock Mode: Returning original video as result.")
            final_video = video 
        
        # Zip Workspace
        shutil.make_archive(str(work_dir/"export"), 'zip', work_dir)
        logs.append("Workspace exported.")
        
        yield packet(v=final_video, f=str(work_dir/"export.zip"))

    except Exception as e:
        traceback.print_exc()
        err = f"Critical Error: {e}\n{traceback.format_exc()}"
        logs.append(err)
        yield packet()

def create_ui():
    css = "body { background-color: #0b0f19; color: white; }"

    with gr.Blocks(title="4DGS Studio", css=css, theme=gr.themes.Soft()) as app:
        gr.Markdown("# ⚡ 4DGS Studio")
        
        with gr.Row():
            with gr.Column():
                video_input = gr.Video(label="Input Sequence")
                fps = gr.Slider(1, 10, value=2, label="FPS Extraction", step=1)
                iterations = gr.Slider(500, 5000, value=1000, label="Iterations")
                colmap = gr.Checkbox(label="Use COLMAP", value=False)
                mock_mode = gr.Checkbox(label="Simulation Mode", value=True)
                start_btn = gr.Button("🚀 Initialize Pipeline", variant="primary")
                export_file = gr.File(label="Download Workspace")

            with gr.Column():
                video_output = gr.Video(label="Rendered Output")
                logs_output = gr.Textbox(label="Console Output", lines=15)
        
        start_btn.click(
            main_pipeline,
            inputs=[video_input, fps, iterations, colmap, mock_mode],
            outputs=[video_output, logs_output, export_file]
        )
        
    return app

if __name__ == "__main__":
    ui = create_ui()
    # Allowing sharing and dynamic port selection
    ui.queue().launch(server_name="127.0.0.1", share=True)
