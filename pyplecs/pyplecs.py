from pathlib import Path
import xmlrpc.client
import subprocess

# Optional imports (Windows-specific GUI automation)
try:
    import pywinauto
    import psutil

    _gui_automation_available = True
except ImportError:
    pywinauto = None
    psutil = None
    _gui_automation_available = False

# Optional imports (MATLAB file I/O)
try:
    import scipy.io as sio
except ImportError:
    sio = None

command = r"C:/Program Files/Plexim/PLECS 4.2 (64 bit)/plecs.exe"
command = r"C:/Program Files/Plexim/PLECS 4.3 (64 bit)/plecs.exe"
# command = r"C:\Users\tinix\Documents\Plexim\PLECS 4.3 (64 bit)\PLECS.exe"


def load_mat_file(file):
    """Load MATLAB .mat file and remove metadata keys."""
    if sio is None:
        raise ImportError(
            "scipy is required for .mat file I/O. Install with: pip install scipy"
        )
    param = sio.loadmat(file)
    del param["__header__"]
    del param["__version__"]
    del param["__globals__"]
    return param


def save_mat_file(file_name, data):
    """Save data to MATLAB .mat file."""
    if sio is None:
        raise ImportError(
            "scipy is required for .mat file I/O. Install with: pip install scipy"
        )
    sio.savemat(file_name, data, format="5")


def dict_to_plecs_opts(varin: dict):
    for k, _ in varin.items():
        varin[k] = float(varin[k])
    opts = {"ModelVars": varin}
    return opts


# DEPRECATED: File-based variant generation removed in v1.0.0
# Use PLECS native ModelVars instead: server.simulate(parameters={"Vi": 12.0, "Vo": 5.0})
# See migration guide for examples.


class PlecsApp:
    def __init__(self):
        self.command = command
        self.app = pywinauto.application.Application(backend="uia")
        self.app.start(self.command)
        self.app_gui = self.app.connect(path=self.command)

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
            subprocess.Popen(
                [command], creationflags=psutil.ABOVE_NORMAL_PRIORITY_CLASS
            ).pid
        except Exception:
            print("Plecs opening problem")

    # return pid

    #    @staticmethod
    def kill_plecs(self):
        proc_iter = psutil.process_iter(attrs=["pid", "name"])
        for p in proc_iter:
            if p.info["name"] == "PLECS.exe":
                # print (p.pid)
                p.kill()

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
        mdl_app = self.app.connect(
            title=str(plecs_mdl._model_name), class_name="Qt5QWindowIcon"
        )
        mdl_app[str(plecs_mdl._name)].set_focus()
        mdl_app[str(plecs_mdl._name)].menu_select("Simulation")
        pywinauto.keyboard.send_keys("{DOWN}")
        pywinauto.keyboard.send_keys("{ENTER}")
        # TBTested
        # pywinauto.keyboard.send_keys('^t')

    def load_file(self, plecs_mdl, mode="XML-RPC"):
        if mode == "gui":
            pwa_app = pywinauto.application.Application()
            qtqwindowicon = pwa_app.connect(
                title="Library Browser", class_name="Qt5QWindowIcon"
            ).Qt5QWindowIcon
            qtqwindowicon.set_focus()
            pywinauto.keyboard.send_keys("^o")
            # TODO: filling window open file
        elif mode == "XML-RPC":
            PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name, load=True)
        else:
            raise Exception("Not implemented mode")

        return None

    def check_if_simulation_running(self, plecs_mdl):
        # TODO: check title of the simulation and return if contain running
        pass


class PlecsServer:
    """Thin wrapper around PLECS XML-RPC with helper methods.

    This class provides a simplified interface to PLECS simulations while
    leveraging PLECS native capabilities (ModelVars, batch parallel API).

    Value-add over direct XML-RPC:
    - Automatic model loading and cleanup via context manager
    - Parameter dict to ModelVars conversion
    - Batch parallel simulation support
    - .mat file I/O integration

    Example:
        # Single simulation
        with PlecsServer("model.plecs") as server:
            results = server.simulate({"Vi": 12.0, "Vo": 5.0})

        # Batch parallel simulations (leverages PLECS native parallelization)
        with PlecsServer("model.plecs") as server:
            params_list = [{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}]
            results = server.simulate_batch(params_list)
    """

    def __init__(
        self, model_file=None, sim_path=None, sim_name=None, port="1080", load=True
    ):
        """Initialize PLECS XML-RPC connection and load model.

        Args:
            model_file: Path to .plecs file (new API, recommended)
            sim_path: Legacy - model directory (deprecated, use model_file)
            sim_name: Legacy - model filename (deprecated, use model_file)
            port: XML-RPC server port (default: 1080)
            load: Whether to load model on initialization (default: True)
        """
        self.server = xmlrpc.client.Server("http://localhost:" + str(port) + "/RPC2")

        # Support both new API (model_file) and legacy API (sim_path + sim_name)
        if model_file is not None:
            model_path = Path(model_file).resolve()
            self.sim_path = str(model_path.parent)
            self.sim_name = model_path.name
            self.modelName = model_path.stem
        elif sim_path is not None and sim_name is not None:
            self.sim_path = sim_path
            self.sim_name = sim_name
            self.modelName = sim_name.replace(".plecs", "")
        else:
            raise ValueError("Must provide either model_file or (sim_path + sim_name)")

        # Load model on initialization if requested
        if load:
            self.server.plecs.load(self.sim_path + "//" + self.sim_name)

    def simulate(self, parameters=None):
        """Run simulation with optional ModelVars parameters.

        This is the primary simulation method. It handles parameter conversion
        and invokes PLECS native simulate() function.

        Args:
            parameters: Dict of model variables (e.g., {"Vi": 12.0, "Vo": 5.0})
                       If None, runs simulation with default model parameters.

        Returns:
            Simulation results from PLECS (structure depends on model outputs)

        Example:
            results = server.simulate({"Vi": 250, "Vo_ref": 25})
        """
        if parameters is None:
            return self.server.plecs.simulate(self.modelName)

        # Convert parameters to PLECS ModelVars format
        opts = dict_to_plecs_opts(parameters)
        return self.server.plecs.simulate(self.modelName, opts)

    def simulate_batch(self, parameter_list):
        """Run batch simulations using PLECS native parallel API.

        CRITICAL: This leverages PLECS' native parallel execution.
        plecs.simulate(mdlName, [optStructs]) automatically distributes
        simulations across CPU cores for maximum performance.

        This is 3-5x faster than sequential execution on multi-core machines.

        Args:
            parameter_list: List of parameter dicts
                           e.g., [{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}]

        Returns:
            List of simulation results (one per parameter set)

        Example:
            params = [{"Vi": 12.0}, {"Vi": 24.0}, {"Vi": 48.0}]
            results = server.simulate_batch(params)
            # PLECS runs these in parallel across available CPU cores
        """
        opt_structs = [dict_to_plecs_opts(params) for params in parameter_list]
        return self.server.plecs.simulate(self.modelName, opt_structs)

    def run_sim_with_mat_file(self, mat_file_path):
        """Run simulation with parameters loaded from .mat file.

        Legacy method for .mat file I/O integration.

        Args:
            mat_file_path: Path to .mat file containing simulation parameters

        Returns:
            Simulation results from PLECS
        """
        inputs = load_mat_file(mat_file_path)
        return self.simulate(inputs)

    # Legacy methods (deprecated but kept for backward compatibility)
    def run_sim_with_datastream(self, param_dict=None):
        """DEPRECATED: Use simulate() instead.

        Kept for backward compatibility. Will be removed in v2.0.0.
        """
        return self.simulate(param_dict)

    def load_modelvars(self, model_vars):
        """DEPRECATED: Parameters are now passed directly to simulate().

        This method is no longer needed. Use simulate(parameters=...) instead.
        Kept for backward compatibility. Will be removed in v2.0.0.
        """
        # Store for legacy compatibility
        if "ModelVars" in model_vars:
            self.optStruct = model_vars
        else:
            self.optStruct = dict_to_plecs_opts(varin=model_vars)

    def set_value(self, ref, parameter, value):
        """Set component parameter value directly via PLECS XML-RPC.

        For most use cases, prefer passing parameters via simulate().
        This method is for advanced use cases requiring direct component access.

        Args:
            ref: Component reference path in model
            parameter: Parameter name
            value: Parameter value
        """
        self.server.plecs.set(self.modelName + "/" + ref, parameter, str(value))

    def close(self):
        """Close the model in PLECS."""
        self.server.plecs.close(self.modelName)

    def __enter__(self):
        """Context manager entry - model already loaded in __init__."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit - close model."""
        self.close()
        return False


# DEPRECATED: GenericConverterPlecsMdl class removed in v1.0.0
# Use PlecsServer class directly with model file path
# Example:
#   with PlecsServer("simple_buck.plecs") as server:
#       results = server.simulate({"Vi": 250, "Vo_ref": 25})


# if __name__ == "__main__":
#    plecs42 = PlecsApp()
#    plecs42.kill_plecs()
#    time.sleep(1)
#    plecs42.open_plecs()
#    time.sleep(1)
#    plecs42.set_plecs_high_priority()
#
#    sim_path = "./"
#    sim_name = "simple_buck.plecs"
