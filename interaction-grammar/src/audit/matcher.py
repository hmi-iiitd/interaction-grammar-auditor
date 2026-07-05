"""
This module provides the logic for matching abstract interaction acts against
concrete trace events.
"""

from typing import Union, List
from src.compiler.ast import Act
from src.audit.trace import Event

class EventMatcher:
    @staticmethod
    def match_act(act_spec: Act, event: Event) -> bool:
        """
        Determines if a trace event satisfies the requirements of an Act node.
        """
        # DEBUG PRINT
        # print(f"Matching {act_spec.object} vs {event.object}")

        # 1. Primitive match
        if act_spec.prim != event.prim:
            return False

        # 2. Channel match
        contract_channels = [c.strip() for c in act_spec.channel.split(',')]
        if event.channel not in contract_channels:
            return False

        # 3. Agent match
        if isinstance(act_spec.agent, list):
            if event.agent not in act_spec.agent:
                return False
        elif act_spec.agent != event.agent:
            return False

        # 4. Object match
        if act_spec.object is not None:
             if act_spec.object != event.object:
                 return False

        return True
