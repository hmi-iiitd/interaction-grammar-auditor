import json
import jsonschema
from pathlib import Path
from typing import Dict, Any

class SchemaValidator:
    def __init__(self, schema_path: str):
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)

    def validate(self, instance: Dict[str, Any]) -> None:
        """
        Validates the given JSON instance against the schema.
        Raises jsonschema.ValidationError if invalid.
        """
        # Optimization: If 'node' is present, validate against that specific definition
        # to get better error messages than "not valid under any of given schemas"
        node_type = instance.get("node")
        if node_type:
            # Map node types to schema definitions
            type_map = {
                "act": "Act",
                "seq": "Seq",
                "par": "Par",
                "neg": "Neg",
                "repair": "Repair",
                "bind": "Bind"
            }
            if node_type in type_map:
                def_name = type_map[node_type]
                # Create a sub-schema that refers to the specific definition
                # We need the full schema context for $refs to work, so we use RefResolver or just validate against the subschema
                # simpler: validate against the definition directly if possible, but $refs might break
                # Best approach with jsonschema: use the definition from the loaded schema
                sub_schema = self.schema["$defs"][def_name]
                # We need to pass the full schema as resolver to handle root refs if any (though here refs are local)
                resolver = jsonschema.validators.RefResolver.from_schema(self.schema)
                jsonschema.validate(instance=instance, schema=sub_schema, resolver=resolver)
                return

        # Fallback to default validation
        jsonschema.validate(instance=instance, schema=self.schema)
