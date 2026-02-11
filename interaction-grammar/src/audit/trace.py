"""
This module handles loading, normalization, and validation of interaction traces.
Traces are sequences of events sorted by timestamp.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

@dataclass
class Event:
    t: float
    prim: str
    agent: str
    channel: str
    object: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "t": self.t,
            "prim": self.prim,
            "agent": self.agent,
            "channel": self.channel
        }
        if self.object is not None:
            d["object"] = self.object
        return d

class TraceError(Exception):
    """Custom exception for trace loading errors."""
    pass

class Trace:
    def __init__(self, events: List[Event]):
        self.events = sorted(events, key=lambda e: e.t)

    @classmethod
    def from_file(cls, path: str) -> 'Trace':
        """Load a trace from a JSONL file."""
        events = []
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise TraceError(f"Trace file not found: {path}")
            
        try:
            with open(path, 'r') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(cls._parse_event(data, line_num))
                    except json.JSONDecodeError as e:
                        raise TraceError(f"Invalid JSON at line {line_num}: {e}")
        except Exception as e:
             if isinstance(e, TraceError):
                 raise
             raise TraceError(f"Failed to read trace file: {e}")

        return cls(events)

    @staticmethod
    def _parse_event(data: Dict[str, Any], line_num: int) -> Event:
        required_fields = ["t", "prim", "agent", "channel"]
        for field in required_fields:
            if field not in data:
                raise TraceError(f"Missing required field '{field}' at line {line_num}")
        
        try:
             t = float(data["t"])
        except ValueError:
             raise TraceError(f"Invalid timestamp at line {line_num}: must be a number")
             
        valid_prims = ["σ", "ρ", "τ", "α"]
        if data["prim"] not in valid_prims:
             raise TraceError(f"Invalid primitive '{data['prim']}' at line {line_num}. Must be one of {valid_prims}")

        return Event(
            t=t,
            prim=data["prim"],
            agent=data["agent"],
            channel=data["channel"],
            object=data.get("object")
        )

    def filter(self, agent: Optional[str] = None, channel: Optional[str] = None) -> 'Trace':
        """Return a new Trace containing only events matching the criteria."""
        filtered_events = [
            e for e in self.events
            if (agent is None or e.agent == agent) and
               (channel is None or e.channel == channel)
        ]
        return Trace(filtered_events)

    def __len__(self):
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    def __getitem__(self, idx):
        return self.events[idx]
