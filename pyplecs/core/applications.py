
"""
PLECS Application Interface Classes
-----------------------------------
Implements the PLECSApp hierarchy for GUI and XRPC server interaction.
Wraps existing process management and XML-RPC logic in a testable, async, OOP interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import subprocess
import psutil
import xmlrpc.client
import asyncio
import logging

class PLECSApp(ABC):
    """Abstract base class for PLECS application interfaces."""
    def __init__(self, executable_path: str):
        self.executable_path = executable_path
        self.is_running = False
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def start(self) -> bool:
        """Start the PLECS application."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the PLECS application."""
        pass

    @abstractmethod
    async def simulate(self, model, **kwargs):
        """Run a simulation with the given model."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the application is healthy and responsive."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the application (for mocking/testing)."""
        pass

class PLECSGUIApp(PLECSApp):
    """PLECS GUI application interface."""
    def __init__(self, executable_path: str, high_priority: bool = False):
        super().__init__(executable_path)
        self.high_priority = high_priority
        self.process: Optional[subprocess.Popen] = None

    async def start(self) -> bool:
        try:
            creation_flags = (psutil.HIGH_PRIORITY_CLASS if self.high_priority
                              else psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            self.process = subprocess.Popen(
                [self.executable_path],
                creationflags=creation_flags
            )
            self.is_running = True
            self.logger.info("PLECS GUI started with PID %s", self.process.pid)
            return True
        except Exception as e:
            self.logger.error("Failed to start PLECS GUI: %s", e)
            return False

    async def stop(self) -> bool:
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
            self.is_running = False
            self.logger.info("PLECS GUI stopped")
            return True
        except Exception as e:
            self.logger.error("Failed to stop PLECS GUI: %s", e)
            return False

    async def simulate(self, model, **kwargs):
        # GUI automation is deprecated; return error or raise
        return {"status": "failed", "error": "GUI automation is deprecated. Use XRPC."}

    async def health_check(self) -> bool:
        # Check if process is alive
        return self.process is not None and self.process.poll() is None

    async def validate_connection(self) -> bool:
        # For GUI, just check process
        return await self.health_check()

class PLECSXRPCApp(PLECSApp):
    """PLECS XRPC server interface."""
    def __init__(self, executable_path: str, port: int = 1080):
        super().__init__(executable_path)
        self.port = port
        self.server_process: Optional[subprocess.Popen] = None
        self._rpc_client: Optional[xmlrpc.client.ServerProxy] = None

    async def start(self) -> bool:
        try:
            cmd = [self.executable_path, '-server', str(self.port)]
            self.server_process = subprocess.Popen(cmd)
            await asyncio.sleep(2)  # Wait for server to start
            self._rpc_client = xmlrpc.client.Server(f'http://localhost:{self.port}/RPC2')
            self.is_running = True
            self.logger.info("PLECS XRPC server started on port %d", self.port)
            return True
        except Exception as e:
            self.logger.error("Failed to start PLECS XRPC server: %s", e)
            return False

    async def stop(self) -> bool:
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
            self._rpc_client = None
            self.is_running = False
            self.logger.info("PLECS XRPC server stopped")
            return True
        except Exception as e:
            self.logger.error("Failed to stop PLECS XRPC server: %s", e)
            return False

    async def simulate(self, model, **kwargs):
        if not self.is_running or not self._rpc_client:
            return {"status": "failed", "error": "XRPC server not running"}
        try:
            # Load model and run simulation
            self._rpc_client.plecs.load(str(model.filename))
            if hasattr(model, 'get_model_vars_opts'):
                opts = model.get_model_vars_opts()
                result = self._rpc_client.plecs.simulate(model.model_name, opts)
            else:
                result = self._rpc_client.plecs.simulate(model.model_name)
            return {"status": "completed", "data": result}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def health_check(self) -> bool:
        try:
            if self._rpc_client:
                # Try a lightweight call
                self._rpc_client.system.listMethods()
                return True
            return False
        except Exception:
            return False

    async def validate_connection(self) -> bool:
        return await self.health_check()
