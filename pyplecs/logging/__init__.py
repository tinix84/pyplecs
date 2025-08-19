"""Structured logging system for PyPLECS."""

import json
import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from ..config import get_config
from ..core.models import LogEntry


class StructuredLogger:
    """Centralized structured logging for PyPLECS."""
    
    def __init__(self):
        self.config = get_config()
        self._setup_logging()
        
        # Create structured logger
        self.logger = structlog.get_logger("pyplecs")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Setup standard logging
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging_config.level))
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        if self.config.logging_config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.logging_config.console_level))
            console_formatter = logging.Formatter(self.config.logging_config.format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.config.logging_config.file_enabled:
            log_file = Path(self.config.logging_config.file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=self._parse_size(self.config.logging_config.file_max_size),
                backupCount=self.config.logging_config.file_backup_count
            )
            file_handler.setLevel(getattr(logging, self.config.logging_config.level))
            file_formatter = logging.Formatter(self.config.logging_config.format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Structured logging handler
        if self.config.logging_config.structured_enabled:
            structured_file = Path(self.config.logging_config.structured_path)
            structured_file.parent.mkdir(parents=True, exist_ok=True)
            
            structured_handler = logging.handlers.RotatingFileHandler(
                filename=structured_file,
                maxBytes=self._parse_size(self.config.logging_config.file_max_size),
                backupCount=self.config.logging_config.file_backup_count
            )
            structured_handler.setLevel(getattr(logging, self.config.logging_config.level))
            
            # Custom formatter for structured logs
            structured_formatter = StructuredFormatter()
            structured_handler.setFormatter(structured_formatter)
            
            # Create separate logger for structured logs
            structured_logger = logging.getLogger("pyplecs.structured")
            structured_logger.addHandler(structured_handler)
            structured_logger.setLevel(getattr(logging, self.config.logging_config.level))
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes."""
        if size_str.upper().endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.upper().endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.upper().endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_simulation_start(self, 
                           task_id: str,
                           model_file: str,
                           parameters: Dict[str, Any],
                           worker_id: Optional[str] = None):
        """Log simulation start."""
        self.logger.info(
            "Simulation started",
            task_id=task_id,
            model_file=model_file,
            parameter_count=len(parameters),
            worker_id=worker_id,
            event_type="simulation_start"
        )
    
    def log_simulation_complete(self,
                              task_id: str,
                              success: bool,
                              execution_time: float,
                              worker_id: Optional[str] = None,
                              cached: bool = False):
        """Log simulation completion."""
        self.logger.info(
            "Simulation completed",
            task_id=task_id,
            success=success,
            execution_time=execution_time,
            worker_id=worker_id,
            cached=cached,
            event_type="simulation_complete"
        )
    
    def log_simulation_error(self,
                           task_id: str,
                           error_message: str,
                           worker_id: Optional[str] = None):
        """Log simulation error."""
        self.logger.error(
            "Simulation failed",
            task_id=task_id,
            error_message=error_message,
            worker_id=worker_id,
            event_type="simulation_error"
        )
    
    def log_cache_hit(self,
                     task_id: str,
                     simulation_hash: str,
                     model_file: str):
        """Log cache hit."""
        self.logger.info(
            "Cache hit",
            task_id=task_id,
            simulation_hash=simulation_hash,
            model_file=model_file,
            event_type="cache_hit"
        )
    
    def log_cache_miss(self,
                      task_id: str,
                      simulation_hash: str,
                      model_file: str):
        """Log cache miss."""
        self.logger.info(
            "Cache miss",
            task_id=task_id,
            simulation_hash=simulation_hash,
            model_file=model_file,
            event_type="cache_miss"
        )
    
    def log_optimization_start(self,
                             request_id: str,
                             algorithm: str,
                             parameter_count: int,
                             objective_count: int):
        """Log optimization start."""
        self.logger.info(
            "Optimization started",
            request_id=request_id,
            algorithm=algorithm,
            parameter_count=parameter_count,
            objective_count=objective_count,
            event_type="optimization_start"
        )
    
    def log_optimization_iteration(self,
                                 request_id: str,
                                 iteration: int,
                                 objective_values: Dict[str, float],
                                 parameter_values: Dict[str, float]):
        """Log optimization iteration."""
        self.logger.debug(
            "Optimization iteration",
            request_id=request_id,
            iteration=iteration,
            objective_values=objective_values,
            parameter_values=parameter_values,
            event_type="optimization_iteration"
        )
    
    def log_optimization_complete(self,
                                request_id: str,
                                success: bool,
                                total_iterations: int,
                                total_simulations: int,
                                execution_time: float):
        """Log optimization completion."""
        self.logger.info(
            "Optimization completed",
            request_id=request_id,
            success=success,
            total_iterations=total_iterations,
            total_simulations=total_simulations,
            execution_time=execution_time,
            event_type="optimization_complete"
        )
    
    def log_api_request(self,
                       endpoint: str,
                       method: str,
                       status_code: int,
                       response_time: float,
                       client_ip: Optional[str] = None):
        """Log API request."""
        self.logger.info(
            "API request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            client_ip=client_ip,
            event_type="api_request"
        )
    
    def log_system_stats(self,
                        cpu_usage: float,
                        memory_usage: float,
                        disk_usage: float,
                        active_tasks: int,
                        queue_size: int):
        """Log system statistics."""
        self.logger.info(
            "System stats",
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            active_tasks=active_tasks,
            queue_size=queue_size,
            event_type="system_stats"
        )
    
    def log_worker_stats(self,
                        worker_id: str,
                        tasks_completed: int,
                        tasks_failed: int,
                        total_runtime: float,
                        is_busy: bool):
        """Log worker statistics."""
        self.logger.info(
            "Worker stats",
            worker_id=worker_id,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            total_runtime=total_runtime,
            is_busy=is_busy,
            event_type="worker_stats"
        )


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            task_id=getattr(record, 'task_id', None),
            worker_id=getattr(record, 'worker_id', None),
            simulation_hash=getattr(record, 'simulation_hash', None),
            metadata={}
        )
        
        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName',
                          'process', 'message', 'exc_info', 'exc_text', 'stack_info',
                          'task_id', 'worker_id', 'simulation_hash']:
                log_entry.metadata[key] = value
        
        return json.dumps(log_entry.to_dict())


# Global logger instance
_structured_logger: Optional[StructuredLogger] = None


def get_logger() -> StructuredLogger:
    """Get the global structured logger instance."""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger


def init_logging() -> StructuredLogger:
    """Initialize the global structured logger."""
    global _structured_logger
    _structured_logger = StructuredLogger()
    return _structured_logger
