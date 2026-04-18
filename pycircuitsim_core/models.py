"""Shared enums and data models for simulation packages."""

from enum import IntEnum


class TaskPriority(IntEnum):
    """Priority values ordered for use in priority queues."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
