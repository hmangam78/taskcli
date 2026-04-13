from datetime import date
from dataclasses import dataclass, field

@dataclass
class Task:
    id: int
    description: str
    tag: str
    insertion_date: date | None = field(default_factory=date.today)
    completion_date: date | None = None
    insertion_date_unknown: bool = False
    completion_date_unknown: bool = False

    def complete_task(self):
        if self.completion_date is None:
            self.completion_date = date.today()
            self.completion_date_unknown = False

    def uncomplete_task(self):
        self.completion_date = None
        self.completion_date_unknown = False
    
