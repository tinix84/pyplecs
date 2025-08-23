import time
import shutil
import os
import subprocess
import psutil
import re
import copy

from pathlib import Path

import xmlrpc.client
import logging
import scipy.io as sio
import socket
import time
# Utilities moved to separate module for testability
from .utils import dict_to_plecs_opts, rpc_call_wrapper

import concurrent.futures
from typing import Optional, Union, Dict, Any
from .exceptions import ModelParsingError, FileLoadError, SimulationError, PlecsConnectionError

# Import configuration system
from .config import ConfigManager


def load_mat_file(file_path: str) -> dict:
    """
    Load MATLAB .mat file and convert to Python dictionary.

    Args:
        file_path: Path to the .mat file.

    Returns:
        A dictionary containing the contents of the .mat file, excluding MATLAB metadata.

    Raises:
        ImportError: If scipy is not installed.
        FileLoadError: If the file cannot be loaded.

    Example:
        >>> data = load_mat_file('example.mat')
        >>> print(data.keys())
        ['variable1', 'variable2']
    """
    try:
        import scipy.io
        mat_data = scipy.io.loadmat(file_path)
        # Filter out MATLAB metadata
        return {k: v for k, v in mat_data.items() if not k.startswith('__')}
    except ImportError:
        raise ImportError("scipy required for .mat file support")
    except Exception as e:
        raise FileLoadError(f"Failed to load .mat file: {str(e)}")


def save_mat_file(file_name: str, data: Dict[str, Any]) -> None:
    """
    Save data to a MATLAB .mat file.

    Args:
        file_name: Path to the .mat file to save.
        data: Dictionary containing data to save.

    Example:
        >>> save_mat_file('output.mat', {'variable1': [1, 2, 3]})
    """
    sio.savemat(file_name, data, format='5')


def generate_variant_plecs_file(scr_filename: str, dst_filename: str, modelvars: Dict[str, Union[int, float]]) -> None:
    """
    Generate a variant PLECS file by modifying initialization commands.

    Args:
        scr_filename: Path to the source PLECS file.
        dst_filename: Path to the destination PLECS file.
        modelvars: Dictionary of model variables to modify.

    Example:
        >>> generate_variant_plecs_file('source.plecs', 'variant.plecs', {'Vin': 400, 'Vout': 200})
    """
    dst_path_obj = Path(dst_filename)

    try:
        os.mkdir(dst_path_obj.parent)
    except FileExistsError:
        shutil.rmtree(dst_path_obj.parent)
        os.mkdir(dst_path_obj.parent)

    fp_src = open(str(scr_filename), "r")
    fp_dst = open(str(dst_filename), "w+")

    state = 'copy'
    for _, line in enumerate(fp_src):
        if start_init_cmd in line:
            state = 'edit'
        if end_init_cmd in line:
            state = 'copy'

        if state == 'edit':
            for var_name, value in modelvars.items():
                regex = var_name + r"([\s\=\d\.]+)\;"
                try:
                    old_var_str = (re.search(regex, line)).group(0)
                    new_var_str = f"{var_name} = {value};"
                    line = line.replace(old_var_str, new_var_str)
                except AttributeError:
                    pass
        fp_dst.writelines(line)

    fp_src.close()
    fp_dst.close()


def generate_variant_plecs_mdl(src_mdl: Any, variant_name: str, variant_vars: Dict[str, Union[int, float]]) -> Any:
    """
    Generate a variant PLECS model by creating a new file with modified variables.

    Args:
        src_mdl: Source PLECS model object.
        variant_name: Name of the variant.
        variant_vars: Dictionary of variables to modify.

    Returns:
        A new PLECS model object with the variant configuration.

    Example:
        >>> variant_model = generate_variant_plecs_mdl(src_model, 'variant1', {'Vin': 400, 'Vout': 200})
    """
    variant_mdl = copy.deepcopy(src_mdl)
    src_path_obj = Path(src_mdl.filename)
    # create folder/name for the variant model and replace extension
    variant_path = src_path_obj.parent / variant_name / src_path_obj.name
    variant_mdl.filename = str(variant_path).replace('.plecs', f'{variant_name}.plecs')
    generate_variant_plecs_file(scr_filename=src_mdl.filename, dst_filename=variant_mdl.filename,
                                modelvars=variant_vars)

    return variant_mdl


class PlecsApp:
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize PlecsApp with configuration-based PLECS path detection.

        Args:
            config_path: Optional path to config file. If None, uses default locations.

        Example:
            >>> app = PlecsApp(config_path='config.yml')
        """
        self.config_manager = ConfigManager(config_path)
        self.command = self._find_plecs_executable()
        # Removed GUI automation functionality - only process management
        self._process = None

    def _find_plecs_executable(self):
        """Find PLECS executable from configuration or common locations."""
        # First try explicit paths from config (if present)
        try:
            exe_paths = list(self.config_manager.plecs.executable_paths or [])
        except Exception:
            exe_paths = []

        for path in exe_paths:
            if Path(path).exists():
                return path

        # Next, try fallback paths defined in config (keeps defaults in YAML)
        try:
            fallback = list(self.config_manager.plecs.fallback_paths or [])
        except Exception:
            fallback = []

        for path in fallback:
            if Path(path).exists():
                return path

        # As last resort, search on PATH for a plecs executable name
        for candidate in ("PLECS.exe", "plecs.exe", "PLECS", "plecs"):
            exe = shutil.which(candidate)
            if exe:
                return exe

        raise FileNotFoundError(
            "PLECS executable not found. Please update config/default.yml (plecs.executable_paths or plecs.fallback_paths) with the correct path."
        )

    #    @staticmethod
    def set_plecs_high_priority(self) -> None:
        """
        Set the PLECS process to high priority.

        Example:
            >>> app.set_plecs_high_priority()
        """
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                # print (p.pid)
                proc = psutil.Process(p.pid)
                proc.nice(psutil.HIGH_PRIORITY_CLASS)

    #    @staticmethod
    def open_plecs(self) -> None:
        """
        Open the PLECS application.

        Example:
            >>> app.open_plecs()
        """
        try:
            pid = subprocess.Popen([self.command], creationflags=psutil.ABOVE_NORMAL_PRIORITY_CLASS).pid
        except Exception:
            print('Plecs opening problem')

    #return pid    #    @staticmethod
    def kill_plecs(self) -> None:
        """
        Terminate the PLECS application process.

        Example:
            >>> app.kill_plecs()
        """
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                # print (p.pid)
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    # Process already terminated or PID reused; ignore
                    continue

    #    @staticmethod
    def get_plecs_cpu(self) -> Optional[float]:
        """
        Get the CPU usage of the PLECS process.

        Returns:
            The CPU usage percentage of the PLECS process, or None if not running.

        Example:
            >>> cpu_usage = app.get_plecs_cpu()
            >>> print(cpu_usage)
        """
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        value = 0
        cpu_usage = None
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                cpu_usage = max(value, p.cpu_percent())
        return cpu_usage

    def run_simulation_by_gui(self, plecs_mdl: Any) -> None:
        """
        GUI simulation is no longer supported. Use XML-RPC instead.

        Args:
            plecs_mdl: PLECS model object.

        Raises:
            NotImplementedError: Always raised as GUI simulation is removed.

        Example:
            >>> app.run_simulation_by_gui(model)
        """
        raise NotImplementedError(
            "GUI automation removed. Use PlecsServer with XML-RPC instead."
        )

    def load_file(self, plecs_mdl: Any, mode: str = 'XML-RPC') -> None:
        """
        Load a PLECS model file.

        Args:
            plecs_mdl: PLECS model object.
            mode: Mode to load the file ('XML-RPC' or 'gui').

        Raises:
            NotImplementedError: If mode is 'gui'.
            Exception: If mode is unsupported.

        Example:
            >>> app.load_file(model, mode='XML-RPC')
        """
        if mode == "gui":
            raise NotImplementedError(
                "GUI mode removed. Use XML-RPC mode instead."
            )
        elif mode == "XML-RPC":
            PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name, load=True)
        else:
            raise Exception("Not implemented mode")

        return None

    def check_if_simulation_running(self, plecs_mdl: Any):
        """Check if simulation is running (placeholder implementation)."""
        # Implemented: multi-strategy detection using XML-RPC, model query,
        # list_running_simulations and psutil process scan as a last resort.
        # plecs_mdl may be:
        # - None: return detailed dict with status summary
        # - str: model name to check
        # - PlecsServer-like object with 'server' attribute
        import time
        start = time.time()

        # Helper: build xmlrpc proxy to default port
        def _get_proxy():
            # default port used elsewhere in the code
            port = '1080'
            try:
                cfg_port = getattr(self.config_manager.plecs, 'rpc_port', None)
                if cfg_port:
                    port = str(cfg_port)
            except Exception:
                # ignore config errors and use default
                pass
            return xmlrpc.client.Server('http://localhost:' + port + '/RPC2')

        # Helper to return detailed dict
        def _detail(result=None, error=None, server_available=False, process_found=False):
            return {
                'server_available': server_available,
                'running': result,
                'process_found': process_found,
                'error': error,
            }

        # If caller passed a PlecsServer-like object, use its proxy
        proxy = None
        model_name = None
        if plecs_mdl is None:
            model_name = None
        elif hasattr(plecs_mdl, 'server'):
            proxy = getattr(plecs_mdl, 'server')
            model_name = getattr(plecs_mdl, 'modelName', None) or getattr(plecs_mdl, 'simulation_name', None)
        elif isinstance(plecs_mdl, str):
            model_name = plecs_mdl.replace('.plecs', '')
        else:
            # attempt to read simulation_name attribute
            model_name = getattr(plecs_mdl, 'simulation_name', None) or getattr(plecs_mdl, 'model_name', None)

        # Try to create a proxy if we don't have one
        if proxy is None:
            try:
                proxy = _get_proxy()
            except Exception as e:
                # Could not create proxy -> fallback to process check
                try:
                    # quick psutil scan
                    proc_found = any(p.info.get('name', '').lower().startswith('plecs') for p in psutil.process_iter(attrs=['name']))
                except Exception:
                    proc_found = False
                # If no proxy and no process, raise connection error
                raise PlecsConnectionError('Cannot connect to PLECS XML-RPC and no PLECS process found') from e

        # Now attempt RPC-based checks within timeout
        try:
            # Primary: try server status helper
            try:
                status = rpc_call_wrapper(proxy, 'plecs.status', retries=1, backoff=0.1)
                # Interpret common status shapes
                if isinstance(status, dict):
                    running = status.get('running', False) or status.get('status', '') == 'running'
                elif isinstance(status, str):
                    running = status.lower() == 'running'
                else:
                    running = bool(status)

                if model_name is None:
                    return _detail(result=running, server_available=True, process_found=False)
                if running:
                    # if server reports running, but model-specific might differ
                    # try model-specific query
                    try:
                        model_status = rpc_call_wrapper(proxy, f'plecs.get', model_name, 'SimulationStatus', retries=1, backoff=0.1)
                        if isinstance(model_status, str):
                            return model_status.lower() == 'running'
                        return bool(model_status)
                    except Exception:
                        return True

            except Exception:
                # status() not available or failed; try list_running_simulations
                try:
                    running_list = rpc_call_wrapper(proxy, 'plecs.list_running_simulations', retries=1, backoff=0.1)
                    if isinstance(running_list, (list, tuple)):
                        if model_name is None:
                            return _detail(result=bool(running_list), server_available=True, process_found=False)
                        return model_name in running_list or (model_name + '.plecs') in running_list
                except Exception:
                    # Next: if model_name provided, try plecs.get(model, 'SimulationStatus')
                    if model_name is not None:
                        try:
                            model_status = rpc_call_wrapper(proxy, 'plecs.get', model_name, 'SimulationStatus', retries=1, backoff=0.1)
                            if isinstance(model_status, str):
                                return model_status.lower() == 'running'
                            return bool(model_status)
                        except Exception:
                            pass

            # If all RPC attempts inconclusive, use a psutil fallback
            try:
                proc_found = any(p.info.get('name', '').lower().startswith('plecs') for p in psutil.process_iter(attrs=['name']))
                # If process exists and no model specified, assume running
                if model_name is None:
                    return _detail(result=proc_found, server_available=True, process_found=proc_found)
                # If model specified, we cannot be sure from process list -> return False
                return False
            except Exception:
                # last resort: return False
                return False

        except Exception as e:
            # Communication error
            raise PlecsConnectionError('Error while querying PLECS server') from e


class PlecsServer:
    def __init__(self, sim_path=None, sim_name=None, port='1080', load=True):
        self.modelName = sim_name.replace('.plecs', '')
        self.server = xmlrpc.client.Server('http://localhost:' + port + '/RPC2')
        self.sim_name = sim_name
        self.sim_path = sim_path
        self.optStruct = None

        if ((sim_path is not None) or ( sim_name is not None)) and load:
            self.server.plecs.load(self.sim_path + '//' + self.sim_name)
        else:
            print('sim_path or sim_path is invalid or load is False')
            print(f'load={load}')

    def run_sim_single(self, inputs, timeout: float = 30.0):
        """Execute a single simulation.

        Args:
            inputs: dict of parameters or path to .mat file

        Returns:
            Standardized result dict
        """
        logger = logging.getLogger(__name__)

        # 1) Load inputs from file if needed
        if isinstance(inputs, str):
            if not Path(inputs).exists():
                raise FileLoadError(f"Input file not found: {inputs}")
            try:
                inputs = load_mat_file(inputs)
            except Exception as e:
                raise FileLoadError(f"Failed to load MAT file: {e}") from e

        if not isinstance(inputs, dict):
            raise ValueError('inputs must be a dict or path to a .mat file')

        # 2) Validate / normalize inputs (coerce to floats where possible)
        try:
            opt = dict_to_plecs_opts(inputs)
        except Exception as e:
            raise ValueError(f'Invalid inputs: {e}') from e

        # merge with existing optStruct if present
        if getattr(self, 'optStruct', None) is None:
            self.optStruct = opt
        else:
            # merge model vars
            base = self.optStruct.get('ModelVars', {})
            merged = {**base, **opt.get('ModelVars', {})}
            self.optStruct = {'ModelVars': merged}

        # 3) Run simulation via RPC with timeout using a thread executor
        start = time.time()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    rpc_call_wrapper,
                    self.server,
                    'plecs.simulate',
                    self.modelName,
                    self.optStruct,
                )
                results = fut.result(timeout=timeout)

            exec_time = time.time() - start
            processed = self._process_simulation_results(results)
            
            # Check if simulation was successful
            simulation_ok = True
            if isinstance(results, dict) and 'SimulationOK' in results:
                simulation_ok = bool(results['SimulationOK'])
            elif hasattr(results, 'SimulationOK'):
                simulation_ok = bool(results.SimulationOK)
            
            if not simulation_ok:
                return {
                    'success': False,
                    'error': 'Simulation failed',
                    'execution_time': exec_time,
                    'parameters_used': self.optStruct.get('ModelVars', {}),
                }
            
            return {
                'success': True,
                'results': processed,
                'execution_time': exec_time,
                'parameters_used': self.optStruct.get('ModelVars', {}),
            }
        except concurrent.futures.TimeoutError as te:
            # attempt to cancel and surface a SimulationError
            try:
                fut.cancel()
            except Exception:
                pass
            logger.exception('PLECS simulation timed out')
            raise SimulationError('PLECS simulation timed out') from te

        except xmlrpc.client.Fault as f:
            logger.exception('PLECS XML-RPC fault during simulate')
            msg = getattr(f, 'faultString', str(f))
            raise SimulationError('PLECS simulation fault: %s' % (msg,)) from f
        except (ConnectionRefusedError, socket.error) as e:
            logger.exception('Connection error when calling PLECS simulate')
            raise PlecsConnectionError('Cannot connect to PLECS server: %s' % (e,)) from e
        except Exception as e:
            logger.exception('Unexpected error during simulation')
            raise SimulationError('Unexpected simulation error: %s' % (e,)) from e

    def _process_simulation_results(self, results):
        """Normalize PLECS simulate output into a Python dict.

        This is intentionally lightweight and accepts dicts or objects with
        Time/Values attributes.
        """
        # If it's already a dict, try to normalize Time/Values
        try:
            import numpy as _np
            HAS_NUMPY = True
        except Exception:
            _np = None
            HAS_NUMPY = False

        try:
            import pandas as _pd
            HAS_PANDAS = True
        except Exception:
            _pd = None
            HAS_PANDAS = False

        if isinstance(results, dict):
            # common keys: 'Time' and 'Values'
            if 'Time' in results and 'Values' in results:
                time_vec = results['Time']
                vals = results['Values']
                if HAS_NUMPY:
                    time_arr = _np.array(time_vec)
                    vals_arr = _np.array(vals)
                else:
                    time_arr = list(time_vec)
                    vals_arr = list(vals)

                if HAS_PANDAS:
                    # build DataFrame with time and signal columns
                    if (HAS_NUMPY and hasattr(vals_arr, 'ndim') and 
                            vals_arr.ndim == 2):
                        # For 2D arrays, each row should be a signal
                        # Create DataFrame with time as index and signals as columns
                        try:
                            if vals_arr.shape[1] == len(time_arr):
                                # Data is in correct orientation
                                df = _pd.DataFrame(vals_arr.T, index=time_arr)
                            elif vals_arr.shape[0] == len(time_arr):
                                # Data needs transposing
                                df = _pd.DataFrame(vals_arr, index=time_arr)
                            else:
                                # Incompatible dimensions - return raw
                                return {
                                    'Time': time_arr,
                                    'Values': vals_arr,
                                    'raw': results
                                }
                            df.index.name = 'Time'
                        except Exception:
                            # Fallback if DataFrame creation fails
                            return {'Time': time_arr, 'Values': vals_arr, 'raw': results}
                    else:
                        # Handle 1D case - ensure lengths match
                        if len(vals_arr) != len(time_arr):
                            # Fallback: return raw data if lengths don't match
                            return {
                                'Time': time_arr,
                                'Values': vals_arr,
                                'raw': results
                            }
                        df = _pd.DataFrame({
                            'Time': time_arr,
                            'Signal_0': vals_arr
                        })
                    return {'dataframe': df, 'raw': results}

                return {'Time': time_arr, 'Values': vals_arr}

        # If object has Time and Values attributes
        if hasattr(results, 'Time') and hasattr(results, 'Values'):
            try:
                time_vec = list(results.Time)
                vals = list(results.Values)
                if HAS_NUMPY:
                    import numpy as _np2
                    time_arr = _np2.array(time_vec)
                    vals_arr = _np2.array(vals)
                else:
                    time_arr = time_vec
                    vals_arr = vals

                if HAS_PANDAS:
                    import pandas as _pd2
                    if hasattr(vals_arr, 'ndim') and vals_arr.ndim == 2:
                        # For 2D arrays, create DataFrame properly
                        try:
                            if vals_arr.shape[1] == len(time_arr):
                                # Data is in correct orientation
                                df = _pd2.DataFrame(vals_arr.T, index=time_arr)
                            elif vals_arr.shape[0] == len(time_arr):
                                # Data needs transposing
                                df = _pd2.DataFrame(vals_arr, index=time_arr)
                            else:
                                # Incompatible dimensions - return raw
                                return {
                                    'Time': time_arr,
                                    'Values': vals_arr,
                                    'raw': results
                                }
                            df.index.name = 'Time'
                        except Exception:
                            # Fallback if DataFrame creation fails
                            return {'Time': time_arr, 'Values': vals_arr, 'raw': results}
                    else:
                        # Handle 1D case - ensure lengths match
                        if len(vals_arr) != len(time_arr):
                            # Fallback: return raw data if lengths don't match
                            return {
                                'Time': time_arr,
                                'Values': vals_arr,
                                'raw': results
                            }
                        df = _pd2.DataFrame({
                            'Time': time_arr,
                            'Signal_0': vals_arr
                        })
                    return {'dataframe': df, 'raw': results}

                return {'Time': time_arr, 'Values': vals_arr}
            except Exception:
                return {'raw': results}

        # Fallback: return raw
        return {'raw': results}

    def load_file(self):
        self.load()

    def load(self):
        """ 
        Interface to the plecs.load function 
        from Plecs help: plecs.load('mdlFileName')
        """
        self.server.plecs.load(self.sim_path + '//' + self.sim_name)

    def close(self):
        """  
        Interface to the plecs.close function 
        from Plecs help: plecs.close('mdlName')
        """
        self.server.plecs.close(self.modelName)

    def load_model_vars(self, data):
        # backward-compat simple wrapper retained for older callers
        # kept to avoid breaking API: delegates to unified implementation
        return self.load_model_vars_unified(data, merge=True, validate=False, convert_types=True)

    def load_model_vars_unified(self, 
                                model_vars, 
                                merge: bool = True,
                                validate: bool = True,
                                convert_types: bool = True) -> dict:
        """Unified loader for model variables supporting multiple input types.

        Args:
            model_vars: dict of variables, or path to .mat / .yaml file (str or Path)
            merge: if True merge into existing ModelVars, else replace
            validate: if True, attempt to validate variable names against model
            convert_types: if True, convert numeric types to float for XML-RPC

        Returns:
            optStruct dict with 'ModelVars'

        Raises:
            FileLoadError for missing/invalid files
            ValueError for validation failures
        """
        # Resolve input source
        data_dict = None
        # If model_vars is a dict-like, use directly
        try:
            from pathlib import Path as _Path
        except Exception:
            _Path = Path

        if isinstance(model_vars, dict):
            data_dict = dict(model_vars)
        elif isinstance(model_vars, (_Path,)) or isinstance(model_vars, str):
            p = _Path(str(model_vars))
            if not p.exists():
                raise FileLoadError(f"Variable file not found: {p}")
            # choose loader by extension
            if p.suffix.lower() in ('.mat',):
                try:
                    data_dict = load_mat_file(str(p))
                except Exception as e:
                    raise FileLoadError(f"Failed to load MAT file: {e}") from e
            elif p.suffix.lower() in ('.yml', '.yaml'):
                try:
                    import yaml as _yaml
                    with p.open('r', encoding='utf-8') as fh:
                        data_dict = _yaml.safe_load(fh) or {}
                except Exception as e:
                    raise FileLoadError(f"Failed to load YAML file: {e}") from e
            else:
                raise FileLoadError(f"Unsupported variable file type: {p.suffix}")
        else:
            raise TypeError('model_vars must be a dict or path to .mat/.yaml file')

        # Ensure flat dict for ModelVars if wrapped in {'ModelVars': {...}}
        if isinstance(data_dict, dict) and 'ModelVars' in data_dict and isinstance(data_dict['ModelVars'], dict):
            vars_in = dict(data_dict['ModelVars'])
        else:
            vars_in = dict(data_dict or {})

        # Optional validation against known model variables
        if validate:
            try:
                allowed = None
                try:
                    allowed = self.get_model_variables()
                except Exception:
                    allowed = None

                if isinstance(allowed, (list, tuple, set)) and len(allowed) > 0:
                    unknown = [k for k in vars_in.keys() if k not in allowed]
                    if unknown:
                        raise ValueError(f"Unknown model variables: {unknown}")
            except Exception:
                # If validation mechanism fails, surface the original exception
                raise

        # Convert types for XML-RPC compatibility
        if convert_types:
            converted = {}
            for k, v in vars_in.items():
                if isinstance(v, (int, float)):
                    converted[k] = float(v)
                else:
                    # leave lists, strings, and other structures intact
                    converted[k] = v
            vars_in = converted

        # Merge or replace into self.optStruct
        existing = {}
        if merge and isinstance(getattr(self, 'optStruct', None), dict):
            existing = dict(self.optStruct.get('ModelVars') or {})

        new_model_vars = {**(existing if merge else {}), **vars_in}
        self.optStruct = {'ModelVars': new_model_vars}
        return self.optStruct

    def load_model_var(self, name, value):
        if not hasattr(self, 'opts'):
            self.optStruct = {'ModelVars': dict()}
        self.optStruct['ModelVars'][name] = float(value)

    def load_model_vars(self, model_vars: Union[dict, str, None], 
                        merge: bool = True, coerce: bool = True, 
                        validate: bool = False) -> dict:
        """
        Unified method for loading model variables.
        
        Args:
            model_vars: Dict of variables or path to file
            merge: If True, merge with existing vars; if False, replace
            coerce: If True, attempt to convert values to float for XML-RPC compatibility
            validate: If True, validate variables against model (requires model variable list)
            
        Returns:
            dict: Updated model variables structure
            
        Raises:
            ValueError: If file type is unsupported or coercion fails
            TypeError: If model_vars is not dict or string
            FileLoadError: If file cannot be loaded
            
        Example:
            >>> server = PlecsServer('models', 'boost.plecs')
            >>> result = server.load_model_vars({'Vin': 400, 'Vout': 200})
            >>> print(result)
            {'ModelVars': {'Vin': 400.0, 'Vout': 200.0}}
        """
        # Handle different input types
        if isinstance(model_vars, str):
            # Assume it's a file path
            if model_vars.endswith('.mat'):
                variables = load_mat_file(model_vars)
            elif model_vars.endswith(('.yml', '.yaml')):
                variables = self._load_yaml_vars(model_vars)
            else:
                raise ValueError(f"Unsupported file type: {model_vars}")
        elif isinstance(model_vars, dict):
            variables = model_vars.copy()
        elif model_vars is None:
            return self.optStruct or {}
        else:
            raise TypeError("model_vars must be dict, file path string, or None")
        
        # Handle the two input formats
        if 'ModelVars' in variables:
            # Already in correct format - normalize values
            base = variables['ModelVars']
        else:
            # Bare dict - needs wrapping
            base = variables

        # Type coercion for XML-RPC compatibility
        normalized = {}
        for k, v in base.items():
            if coerce:
                try:
                    # Try to convert to float for XML-RPC
                    if isinstance(v, (int, float)):
                        normalized[k] = float(v)
                    elif isinstance(v, str):
                        # Try parsing numeric strings
                        v_stripped = v.strip()
                        try:
                            normalized[k] = float(v_stripped)
                        except ValueError:
                            # Keep as string for expressions
                            normalized[k] = v
                    else:
                        normalized[k] = float(v)
                except (ValueError, TypeError):
                    if validate:
                        raise ValueError(f"Cannot coerce variable '{k}' with value '{v}' to numeric type")
                    normalized[k] = v
            else:
                normalized[k] = v

        # Process the variables into correct format
        processed_vars = {'ModelVars': normalized}
        
        # Initialize optStruct if needed
        if not hasattr(self, 'optStruct') or self.optStruct is None:
            self.optStruct = {}
        
        # Merge or replace
        if merge and 'ModelVars' in self.optStruct:
            current_vars = self.optStruct.get('ModelVars', {})
            current_vars.update(processed_vars['ModelVars'])
            processed_vars['ModelVars'] = current_vars
        
        # Store the result
        self.optStruct.update(processed_vars)
        return self.optStruct

    def _load_yaml_vars(self, file_path: str) -> dict:
        """
        Load variables from YAML file.
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Dictionary of variables loaded from YAML
            
        Raises:
            ImportError: If PyYAML is not installed
            FileLoadError: If file cannot be loaded
        """
        try:
            import yaml
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            raise ImportError("PyYAML required for .yml/.yaml file support")
        except Exception as e:
            raise FileLoadError(f"Failed to load YAML file: {str(e)}")

    def load_modelvars(self, model_vars: dict):
        import warnings
        warnings.warn(
            "load_modelvars() is deprecated, use load_model_vars()",
            DeprecationWarning,
            stacklevel=2,
        )
        # Preserve previous behavior: accept both {'ModelVars': {...}} and plain dict
        if isinstance(model_vars, dict) and 'ModelVars' in model_vars:
            self.optStruct = model_vars
            return self.optStruct
        # otherwise delegate to the new unified loader (merge by default)
        return self.load_model_vars(model_vars, merge=True, validate=False, coerce=True)

    def set_value(self, ref, parameter, value):
        self.server.plecs.set(self.modelName + '/' + ref, parameter, str(value))

    def get(self, componentPath, parameter=None):
        """
        Wrapper for plecs.get. If parameter is provided returns the specific
        parameter value, otherwise returns the dict/struct of all parameters
        for the component path.
        """
        if parameter is None:
            return self.server.plecs.get(componentPath)
        return self.server.plecs.get(componentPath, parameter)

    def get_model_variables(self):
        """Return a list of model variable names.

        Attempt to call the RPC helper `plecs.getModelVariables()` on the
        connected server. If the method is not available (Fault -32601) or
        the RPC object doesn't expose it, fall back to parsing the local
        .plecs model file using `plecs_parser.parse_plecs_file()` and return
        the keys of the `init_vars` dict.
        """
        logger = logging.getLogger(__name__)
        # First try RPC call if available
        try:
            if hasattr(self.server, 'plecs') and hasattr(self.server.plecs, 'getModelVariables'):
                try:
                    mv = self.server.plecs.getModelVariables()
                    if isinstance(mv, (list, tuple)):
                        return list(mv)
                    return mv
                except xmlrpc.client.Fault as f:
                    # -32601 = method not found; log and fall back
                    if getattr(f, 'faultCode', None) != -32601:
                        logger.error('RPC fault when calling getModelVariables: %s', f)
                        raise
                    logger.debug('RPC does not expose getModelVariables (fault -32601). Falling back to parser.')
        except AttributeError:
            logger.debug('RPC proxy does not expose getModelVariables attribute; falling back to parser.')

        # Fallback: attempt to locate the local .plecs file in several places
        try:
            from .plecs_parser import parse_plecs_file

            candidates = []
            # prefer explicit sim_path when provided
            if getattr(self, 'sim_path', None):
                candidates.append(Path(self.sim_path) / (self.sim_name or ''))
            # direct sim_name (may be absolute or relative)
            if self.sim_name:
                candidates.append(Path(self.sim_name))
                candidates.append(Path.cwd() / self.sim_name)

            # try repository data folder relative to this file (repo_root/data)
            repo_root = Path(__file__).resolve().parents[2]
            candidates.append(repo_root / 'data' / (self.sim_name or ''))

            # search candidates for existence, and as a last resort try to find
            # a .plecs file with the same stem anywhere under the repo
            model_file = None
            for c in candidates:
                try:
                    if c and c.exists():
                        model_file = c
                        break
                except Exception:
                    continue

            if model_file is None and self.sim_name:
                stem = Path(self.sim_name).stem
                for p in repo_root.rglob('*.plecs'):
                    if p.stem == stem:
                        model_file = p
                        break

            if model_file is None:
                raise FileNotFoundError(f"Could not locate .plecs file for model '{self.sim_name}'")

            logger.debug('Using model file %s for parser fallback', model_file)
            parsed = parse_plecs_file(str(model_file))
            return list(parsed.get('init_vars', {}).keys())
        except Exception as e:
            logger.error('Failed to retrieve model variables via RPC or parser: %s', e)
            raise RuntimeError('Could not retrieve model variables via RPC or parser') from e

    def list_model_variables(self):
        """Return tuple (ok, vars_or_error). ok=True on success and vars is list.

        On failure ok=False and the second element is an error message.
        """
        try:
            vars = self.get_model_variables()
            return True, vars
        except Exception as e:
            return False, str(e)

    def export_scope_csv(self, scope_path, file_name, time_range=None):
        """
    Wrapper for plecs.scope(scope_path, 'ExportCSV', file_name[, time_range]).
    If time_range is provided it should be an iterable like [t1, t2].
    Returns whatever the RPC server returns (usually None or a file path).
        """
        if time_range is None:
            return self.server.plecs.scope(scope_path, 'ExportCSV', file_name)
        return self.server.plecs.scope(scope_path, 'ExportCSV', file_name, time_range)

    def run_sim_with_datastream(self, param_dict=None):
        """
        Kick off PLECS simulation with specified
        @param param_dict parameter dictionary for the PLECS circuit
        @return simulation data in case ouput is present in the model
        """
        if param_dict is None:
            return self.server.plecs.simulate(self.modelName)
        else:
            self.load_modelvars(model_vars=param_dict)
            return self.server.plecs.simulate(self.modelName, self.optStruct)

    def simulate_batch(self, optStructs, callback=None):
        """
        Run multiple simulations by passing a list (1xN) of option structures
        to the PLECS RPC simulate command. This mirrors the documented
        behaviour where plecs.simulate(modelName, optStructs) returns a list
        of results.

        If `callback` is provided (a Python callable), it will be invoked for
        each result as callback(index, result) and the list of callback return
        values will be returned. If no callback is provided, the raw list of
        results from the XML-RPC call is returned.

        Note: the callback is executed locally after receiving the results
        from the RPC server (the RPC API does not support sending a remote
        function pointer via xmlrpc.client), but this provides the same
        convenience for client-side aggregation.
        """
        if not isinstance(optStructs, (list, tuple)):
            raise TypeError("optStructs must be a list or tuple of option structs")

        # Call remote simulate with the list of optStructs
        results = self.server.plecs.simulate(self.modelName, list(optStructs))

        # If no callback provided return raw results
        if callback is None:
            return results

        if not callable(callback):
            raise TypeError("callback must be callable")

        callback_outputs = []
        for idx, res in enumerate(results):
            callback_outputs.append(callback(idx, res))

        return callback_outputs


class GenericConverterPlecsMdl:
    def __init__(self, filename: str):
        # simulation file
        path_obj = Path(filename)
        self._type = path_obj.suffix[1:]
        self._folder = path_obj.parent
        self._name = path_obj.name  # PLECS Model name with filetype extension
        self._model_name = self._name.replace('.plecs', '')
        self._fullname = path_obj
        # simulation vars
        self.optStruct = self.set_default_model_vars()
        # I/O section
        self.components_vars = {}
        self.outputs_vars = {}
        # server section
        # self.server = PlecsServer(sim_path=str(self._folder), sim_name=self._name)

    def __repr__(self) -> str:
        """
        String representation of the PLECS model.

        Returns:
            A string containing the model name, folder, type, and number of model variables.

        Example:
            >>> mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
            >>> print(repr(mdl))
            "GenericConverterPlecsMdl(name='simple_buck', folder='data', type='plecs', model_vars=14)"
        """
        return (
            f"GenericConverterPlecsMdl("
            f"name='{self._model_name}', "
            f"folder='{self._folder}', "
            f"type='{self._type}', "
            f"model_vars={len(self.optStruct.get('ModelVars', {}))}"
            f")"
        )

    # def load_modelvars_struct_from_plecs(self):
    #     # TODO: read parameter list from .plecs file (parser)
    #     pass

    # def load_input_vars(self):
    #     # TODO: read from workspace write to plecs file
    #     pass

    def set_default_model_vars(self) -> dict:
        """
        Set default model variables based on model type.

        Returns:
            A dictionary containing default simulation parameters and model variables.

        Example:
            >>> mdl = GenericConverterPlecsMdl('converter_model.plecs')
            >>> defaults = mdl.set_default_model_vars()
            >>> print(defaults)
            {
                'SimulationTime': 0.001,
                'StepSize': 1e-6,
                'RelTol': 0.001,
                'AbsTol': 1e-6,
                'MaxStepSize': 0.0001,
                'ModelVars': {
                    'Vin': 400.0,
                    'Vout': 200.0,
                    'Pout': 1000.0,
                    'fsw': 20000.0
                }
            }
        """
        defaults = {
            'SimulationTime': 1e-3,
            'StepSize': 1e-6,
            'RelTol': 1e-3,
            'AbsTol': 1e-6,
            'MaxStepSize': 1e-4,
            'ModelVars': {}
        }

        # Add model-type specific defaults
        if 'converter' in self._name.lower():
            defaults['ModelVars'].update({
                'Vin': 400.0,
                'Vout': 200.0,
                'Pout': 1000.0,
                'fsw': 20000.0
            })

        return defaults

    def get_file_info(self) -> dict:
        """Return basic file information: size (bytes) and modification time (ISO).

        Raises FileNotFoundError if file does not exist.
        """
        p = Path(self._fullname)
        if not p.exists():
            raise FileNotFoundError(f"PLECS model file not found: {p}")
        stat = p.stat()
        return {
            'file': str(p),
            'size': stat.st_size,
            'modified': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(stat.st_mtime)),
            'exists': True,
        }

    def validate_model(self) -> bool:
        """Quick validation of the model file: checks extension and readability.

        Returns True when file exists and has a supported extension (primarily '.plecs').
        """
        p = Path(self._fullname)
        if not p.exists():
            return False
        ext = p.suffix.lower().lstrip('.')
        # support 'plecs' and common XML-backed variants
        return ext in ('plecs', 'xml')

    def load_modelvars_struct_from_plecs(self) -> dict:
        """
        Extract model variables structure from PLECS file.

        Returns:
            A dictionary containing the model variables.

        Raises:
            ModelParsingError: If the model variables cannot be parsed.

        Example:
            >>> mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
            >>> vars = mdl.load_modelvars_struct_from_plecs()
            >>> print(vars)
            {'Vi': 400, 'Vo': 200}
        """
        try:
            model_vars = self._parse_plecs_file_variables()
            self.optStruct.update({'ModelVars': model_vars})
            return model_vars
        except Exception as e:
            raise ModelParsingError(f"Failed to parse model variables: {str(e)}")

    def _parse_plecs_file_variables(self) -> dict:
        """
        Internal method to parse PLECS file for variables.

        Returns:
            A dictionary containing initialized variables and parameters.

        Example:
            >>> mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
            >>> vars = mdl._parse_plecs_file_variables()
            >>> print(vars)
            {'Vi': 400, 'Vo': 200}
        """
        # Implementation for parsing PLECS XML structure
        pass

    def get_model_info(self) -> dict:
        """
        Get comprehensive model information.

        Returns:
            A dictionary containing model name, file path, type, folder, model variables, components, and outputs.

        Example:
            >>> mdl = GenericConverterPlecsMdl('data/simple_buck.plecs')
            >>> info = mdl.get_model_info()
            >>> print(info)
            {'name': 'simple_buck', 'file_path': 'data/simple_buck.plecs', 'type': 'plecs', 'folder': 'data', 'model_vars': {...}, 'components': {...}, 'outputs': {...}}
        """
        return {
            'name': self._model_name,
            'file_path': str(self._fullname),
            'type': self._type,
            'folder': str(self._folder),
            'model_vars': self.optStruct.get('ModelVars', {}),
            'components': self.components_vars,
            'outputs': self.outputs_vars
        }

