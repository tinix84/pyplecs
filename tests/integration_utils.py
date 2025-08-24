import time
from pathlib import Path
from pyplecs import PlecsApp, PlecsServer, plecs_parser

# Update PlecsParser references
parse_plecs_file = plecs_parser.parse_plecs_file

def start_plecs_app():
    app = PlecsApp()
    app.kill_plecs()
    time.sleep(1)
    app.open_plecs()
    time.sleep(2)
    app.set_plecs_high_priority()
    return app

def load_and_validate_model(model_path):
    assert Path(model_path).exists(), f"Model file not found: {model_path}"
    parsed_data = parse_plecs_file(model_path)
    model_vars = parsed_data.get('init_vars', {})
    return parsed_data, model_vars

def start_xrpc_server(model_folder, model_name, port=1080):
    server = PlecsServer(model_folder, model_name, port=port, load=True)
    return server

def filter_sweep_params(sweep_dict, allowed_vars):
    return {k: v for k, v in sweep_dict.items() if k in allowed_vars}

def setup_plecs_app():
    return start_plecs_app()

def setup_plecs_server(app, model_folder, model_name):
    return start_xrpc_server(model_folder, model_name)
