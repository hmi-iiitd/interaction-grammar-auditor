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
        
        Matching rules:
        1. Primitive (prim) must match exactly.
        2. Channel must match exactly.
        3. Agent must match:
           - If act_spec.agent is a string, exact match.
           - If act_spec.agent is a list, event.agent must be in the list.
        4. Object:
           - If act_spec.object is present, it must match event.object exactly.
           - If act_spec.object is None, we ignore event.object (allow any).
        """
        # 1. Primitive match
        if act_spec.prim != event.prim:
            return False
            
        # 2. Channel match
        if act_spec.channel != event.channel:
            return False
            
        # 3. Agent match
        if isinstance(act_spec.agent, list):
            if event.agent not in act_spec.agent:
                return False
        elif act_spec.agent != event.agent:
            return False
            
        # 4. Object match
        # If the contract specifies an object, the event must match it.
        # If the contract does NOT specify an object, we assume it's a "don't care" (wildcard)
        if act_spec.object is not None:
             if act_spec.object != event.object:
                 return False
                 
        return True
