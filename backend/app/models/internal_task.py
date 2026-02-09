from __future__ import annotations

from enum import Enum


class InternalTaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class InternalTaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


INTERNAL_TASK_MUTABLE_STATUSES: dict[InternalTaskStatus, set[InternalTaskStatus]] = {
    InternalTaskStatus.TODO: {InternalTaskStatus.IN_PROGRESS, InternalTaskStatus.DONE},
    InternalTaskStatus.IN_PROGRESS: {InternalTaskStatus.TODO, InternalTaskStatus.DONE},
    InternalTaskStatus.DONE: {InternalTaskStatus.IN_PROGRESS},
}
