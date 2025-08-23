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


class SimulationError(Exception):
    """Raised when a simulation fails or times out."""


class FileLoadError(Exception):
    """Raised when input file cannot be loaded for simulation."""



class PlecsConnectionError(Exception):
    """Raised when unable to contact PLECS XML-RPC or determine status."""

# Import configuration system
from .config import ConfigManager


def load_mat_file(file):
    param = sio.loadmat(file)
    del param['__header__']
    del param['__version__']
    del param['__globals__']
    return param


def save_mat_file(file_name, data):
    sio.savemat(file_name, data, format='5')


# dict_to_plecs_opts is provided by pyplecs.utils


def generate_variant_plecs_file(scr_filename: str, dst_filename: str, modelvars: dict):
    # keyword grammar for parser
    start_init_cmd = 'InitializationCommands'
    end_init_cmd = 'InitialState'

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


def generate_variant_plecs_mdl(src_mdl, variant_name: str, variant_vars: dict):
    variant_mdl = copy.deepcopy(src_mdl)
    src_path_obj = Path(src_mdl.filename)
    # create folder/name for the variant model and replace extension
    variant_path = src_path_obj.parent / variant_name / src_path_obj.name
    variant_mdl.filename = str(variant_path).replace('.plecs', f'{variant_name}.plecs')
    generate_variant_plecs_file(scr_filename=src_mdl.filename, dst_filename=variant_mdl.filename,
                                modelvars=variant_vars)

    return variant_mdl


class PlecsApp:
    def __init__(self, config_path=None):
        """Initialize PlecsApp with configuration-based PLECS path detection.
        
        Args:
            config_path: Optional path to config file. 
                        If None, uses default locations.
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
    def set_plecs_high_priority(self):
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                # print (p.pid)
                proc = psutil.Process(p.pid)
                proc.nice(psutil.HIGH_PRIORITY_CLASS)

    #    @staticmethod
    def open_plecs(self):
        try:
            pid = subprocess.Popen([self.command], creationflags=psutil.ABOVE_NORMAL_PRIORITY_CLASS).pid
        except Exception:
            print('Plecs opening problem')
    #return pid    #    @staticmethod
    def kill_plecs(self):
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
    def get_plecs_cpu(self):
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        value = 0
        cpu_usage = None
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                cpu_usage = max(value, p.cpu_percent())
        return cpu_usage

    def run_simulation_by_gui(self, plecs_mdl):
        """GUI simulation is no longer supported. Use XML-RPC instead."""
        raise NotImplementedError(
            "GUI automation removed. Use PlecsServer with XML-RPC instead."
        )

    def load_file(self, plecs_mdl, mode='XML-RPC'):
        """Load PLECS model file."""
        if mode == "gui":
            raise NotImplementedError(
                "GUI mode removed. Use XML-RPC mode instead."
            )
        elif mode == "XML-RPC":
            PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name, load=True)
        else:
            raise Exception("Not implemented mode")
        
        return None

    def check_if_simulation_running(self, plecs_mdl):
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
                    if HAS_NUMPY and vals_arr.ndim == 2:
                        df = _pd.DataFrame(vals_arr)
                        df.insert(0, 'Time', time_arr)
                    else:
                        df = _pd.DataFrame({'Time': time_arr, 'Signal_0': vals_arr})
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
                        df = _pd2.DataFrame(vals_arr)
                        df.insert(0, 'Time', time_arr)
                    else:
                        df = _pd2.DataFrame({'Time': time_arr, 'Signal_0': vals_arr})
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
        varin = {**self.optStruct['ModelVars'], **data}
        for k, _ in varin.items():
            varin[k] = float(varin[k])  # float conversion due to XML protocol limitation
        opts = {'ModelVars': varin}
        return opts

    def load_model_var(self, name, value):
        if not hasattr(self, 'opts'):
            self.optStruct = {'ModelVars': dict()}
        self.optStruct['ModelVars'][name] = float(value)

    def load_modelvars(self, model_vars: dict):
        #TODO: merge with load_model_vars
        if 'ModelVars' in model_vars:
            # self.optStruct = {'ModelVars': dict()}
            self.optStruct = model_vars
        else:
            self.optStruct = dict_to_plecs_opts(varin=model_vars)

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

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        try:
            return (
                f"GenericConverterPlecsMdl(filename='{self.filename}', "
                f"model_name='{self.model_name}')"
            )
        except Exception:
            # Fallback minimal repr
            nm = getattr(self, '_name', None)
            return "GenericConverterPlecsMdl(name=%s)" % (nm,)

    # def load_modelvars_struct_from_plecs(self):
    #     # TODO: read parameter list from .plecs file (parser)
    #     pass

    # def load_input_vars(self):
    #     # TODO: read from workspace write to plecs file
    #     pass

    def set_default_model_vars(self):
        varin = dict()
        varin['Vi'] = 0.0
        varin['Vo'] = 0.0
        # convert each item to float (XLM-RPC doesnt support numpy type)
        for k, _ in varin.items():
            varin[k] = float(varin[k])
        opts = {'ModelVars': varin}
        return opts

    @property
    def filename(self):
        ''' PLECS Model name with filetype extension and full address '''
        return str(self._fullname)

    @property
    def folder(self):
        ''' PLECS Model folder full address '''
        return str(self._folder)

    @property
    def model_name(self):
        ''' PLECS Model name without filetype extension '''
        return str(self._model_name)

    @property
    def simulation_name(self):
        ''' PLECS Model name with filetype extension '''
        return str(self._name)

    @filename.setter
    def filename(self, filename: str):
        path_obj = Path(filename)
        self._type = path_obj.suffix
        self._folder = path_obj.parent
        self._name = path_obj.name
        self._fullname = path_obj
        self._model_name = self._name.replace('.plecs', '')

