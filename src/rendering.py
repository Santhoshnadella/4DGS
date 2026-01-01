
import sys
import os
import torch
import logging
from pathlib import Path
import cv2
import numpy as np
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_LIB = REPO_ROOT / "4DGaussians"
if str(EXTERNAL_LIB) not in sys.path:
    sys.path.insert(0, str(EXTERNAL_LIB))

try:
    from render import render_sets
    from scene import Scene, GaussianModel
    from gaussian_renderer import render
    from arguments import ModelParams, PipelineParams, ModelHiddenParams, get_combined_args
    from argparse import ArgumentParser
except ImportError as e:
    logging.warning(f"Rendering imports failed: {e}")

def render_video(model_path, output_path, fps=30):
    """
    Invokes the rendering pipeline to generate video.
    """
    model_path = Path(model_path)
    output_path = Path(output_path)
    
    # Setup args similar to render.py
    parser = ArgumentParser()
    lp = ModelParams(parser)
    pp = PipelineParams(parser)
    hp = ModelHiddenParams(parser)
    
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--skip_train", action="store_true")
    parser.add_argument("--skip_test", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--skip_video", action="store_true")
    parser.add_argument("--configs", type=str)
    
    # We assume 'config.py' is in the model path or we pass it
    config_file = model_path.parent / "config.py"
    
    cmd_args = [
        "--model_path", str(model_path),
        "--skip_train",
        "--skip_test",
        "--configs", str(config_file)
    ]
    
    args = get_combined_args(parser, cmd_args)
    
    if args.configs:
        import mmcv
        from utils.params_utils import merge_hparams
        config = mmcv.Config.fromfile(args.configs)
        args = merge_hparams(args, config)

    # Invoke render sets
    try:
        render_sets(
            lp.extract(args),
            hp.extract(args),
            args.iteration,
            pp.extract(args),
            args.skip_train,
            args.skip_test,
            args.skip_video
        )
        
        # 4DGaussians render.py saves a video in model_path/video/ours_{iter}/video_rgb.mp4
        # We need to find it and move it to output_path
        
        # Heuristic to find the generated video
        potential_videos = list(model_path.glob("**/video_rgb.mp4"))
        if potential_videos:
            import shutil
            shutil.copy(str(potential_videos[0]), str(output_path))
            return str(output_path)
        else:
            return None
            
    except Exception as e:
        logging.error(f"Rendering failed: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None
