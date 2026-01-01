
import sys
from pathlib import Path
import logging
import torch
import traceback
from argparse import ArgumentParser

# Add 4DGaussians to path
REPO_ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_LIB = REPO_ROOT / "4DGaussians"
if str(EXTERNAL_LIB) not in sys.path:
    sys.path.insert(0, str(EXTERNAL_LIB))

try:
    from train import training
    from scene import Scene, GaussianModel
    from arguments import ModelParams, PipelineParams, OptimizationParams, ModelHiddenParams
    from utils.general_utils import safe_state
except ImportError as e:
    logging.warning(f"Could not import 4DGaussians modules: {e}")

class MonitorCallback:
    def __init__(self, callback_fn):
        self.callback = callback_fn
        
    def __call__(self, iteration, losses):
        if self.callback:
            self.callback(iteration, losses)

def train_model(data_dir, config_path, iterations=3000, monitor_callback=None):
    """
    Executes the training loop of 4DGaussians using the provided configuration.
    """
    # 1. Setup Arguments just like train.py
    parser = ArgumentParser(description="Training script parameters")
    
    lp = ModelParams(parser)
    op = OptimizationParams(parser)
    pp = PipelineParams(parser)
    hp = ModelHiddenParams(parser)
    
    # Add default args expected by the parser
    parser.add_argument('--ip', type=str, default="127.0.0.1")
    parser.add_argument('--port', type=int, default=6009)
    parser.add_argument('--debug_from', type=int, default=-1)
    parser.add_argument('--detect_anomaly', action='store_true', default=False)
    parser.add_argument("--test_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--save_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=[])
    parser.add_argument("--start_checkpoint", type=str, default=None)
    parser.add_argument("--expname", type=str, default="custom_exp")
    parser.add_argument("--configs", type=str, default=str(config_path))
    
    # Emulate command line args
    # We need to construct the args list to pass to parser.parse_args
    # Or manually set values on the Result object. 
    # The 'extract' methods usually take the parsed args object.
    
    cmd_args = [
        "--source_path", str(data_dir),
        "--model_path", str(Path(data_dir) / "output"),
        "--iterations", str(iterations),
        "--configs", str(config_path),
        "--images", "frames",
        "--resolution", "2"
    ]
    
    args = parser.parse_args(cmd_args)
    
    # Merge config file params (logic from train.py)
    if args.configs:
        import mmcv
        from utils.params_utils import merge_hparams
        config = mmcv.Config.fromfile(args.configs)
        args = merge_hparams(args, config)
    
    # 2. Initialize
    safe_state(args.quiet)
    # Network GUI skipped to avoid blocked ports/threading issues in Gradio
    
    # 3. Custom Progress Wrapper
    # 4DGaussians train.py doesn't accept a callback directly in 'training'.
    # We might need to monkey-patch or just accept that we can't get real-time callbacks 
    # without modifying their code.
    # HOWEVER, we can run it in a thread and monitor the log file or output folder?
    # For now, we will run it synchronously.
    
    try:
        training(
            lp.extract(args), 
            hp.extract(args), 
            op.extract(args), 
            pp.extract(args), 
            args.test_iterations, 
            args.save_iterations, 
            args.checkpoint_iterations, 
            args.start_checkpoint, 
            args.debug_from, 
            args.expname
        )
    except Exception as e:
        logging.error(f"Training failed: {e}")
        logging.error(traceback.format_exc())
        raise

    return str(args.model_path)

def create_config_file(base_dir, config_dict):
    """Creates a config file compatible with mmcv/4DGaussians"""
    base_dir = Path(base_dir)
    config_path = base_dir / "config.py"
    
    # Simplified config content based on 4DGaussians requirements
    content = f"""
model_path = "{str(base_dir / 'output').replace('\\', '/')}"
source_path = "{str(base_dir).replace('\\', '/')}"
iterations = {config_dict.get('iterations', 3000)}

# Standard 4DGS defaults
sh_degree = 3
white_background = False  
    """
    with open(config_path, "w") as f:
        f.write(content)
        
    return str(config_path)
