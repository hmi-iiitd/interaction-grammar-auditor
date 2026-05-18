import os
import sys
import uuid
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple
from fastapi import UploadFile, HTTPException

# Add the root directory to path to allow importing interaction-grammar
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
IG_DIR = ROOT_DIR / "interaction-grammar"
sys.path.append(str(IG_DIR))

try:
    from src.compiler.validator import SchemaValidator, SemanticValidator, ValidationError
    from src.compiler.parser import ContractParser, ParserError
    from jsonschema import ValidationError as JsonSchemaError
except ImportError as e:
    print(f"Warning: Failed to import interaction-grammar modules: {e}")

from transformer import audit_mapper
from config import get_settings

def get_dataset_root() -> Path:
    settings = get_settings()
    root = Path(settings.dataset_root)
    if not root.is_absolute():
        root = Path(__file__).parent.parent.parent / root
    return root.resolve()

class UploadError(Exception):
    pass

def validate_contract_file(contract_file: UploadFile = None, contract_text: str = None) -> Dict[str, Any]:
    """Validates a contract file without full scenario processing."""
    try:
        if contract_file:
            content = contract_file.file.read()
            contract_data = json.loads(content)
        elif contract_text:
            contract_data = json.loads(contract_text)
        else:
            raise UploadError("No contract file or text provided")

        schema_path = IG_DIR / "schema" / "schema.json"
        if schema_path.exists():
            schema_validator = SchemaValidator(str(schema_path))
            try:
                schema_validator.validate(contract_data)
            except JsonSchemaError as e:
                raise UploadError(f"Contract Schema Validation Error: {e.message}")

        try:
            parser = ContractParser()
            ast = parser.parse(contract_data)
            semantic_validator = SemanticValidator()
            semantic_validator.validate(ast)
        except (ParserError, ValidationError) as e:
            raise UploadError(f"Contract Semantic Error: [{e.code}] {e.message}")

        return {"status": "success", "message": "Contract is valid!"}
    except UploadError:
        raise
    except Exception as e:
        raise UploadError(str(e))

def handle_upload(
    scenario_id: str,
    contract_file: UploadFile = None,
    contract_text: str = None,
    trace_file: UploadFile = None,
    interaction_type: str = "Turn-taking / acknowledgment",
    robot_platform: str = "NAO",
) -> Dict[str, Any]:
    """
    Handles the end-to-end upload process:
    1. Saves files to a temp dir
    2. Validates Contract schema and semantics
    3. Extracts trace from bag (if needed)
    4. Audits trace
    5. Transforms and saves to dataset/
    """
    temp_dir = Path(f"/tmp/ig_upload_{uuid.uuid4().hex}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Save uploaded files
        contract_path = temp_dir / "contract.ig.json"
        
        if contract_file:
            with open(contract_path, "wb") as f:
                f.write(contract_file.file.read())
        elif contract_text:
            with open(contract_path, "w") as f:
                f.write(contract_text)
        else:
            raise UploadError("No contract file or text provided")

        original_ext = Path(trace_file.filename).suffix
        trace_path = temp_dir / f"uploaded_trace{original_ext}"
        with open(trace_path, "wb") as f:
            f.write(trace_file.file.read())

        # 2. Validate Contract
        try:
            with open(contract_path, "r") as f:
                contract_data = json.load(f)
        except json.JSONDecodeError as e:
            raise UploadError(f"Invalid JSON in contract file: {e}")

        schema_path = IG_DIR / "schema" / "schema.json"
        if schema_path.exists():
            schema_validator = SchemaValidator(str(schema_path))
            try:
                schema_validator.validate(contract_data)
            except JsonSchemaError as e:
                raise UploadError(f"Contract Schema Validation Error: {e.message}")

        try:
            parser = ContractParser()
            ast = parser.parse(contract_data)
            semantic_validator = SemanticValidator()
            semantic_validator.validate(ast)
        except (ParserError, ValidationError) as e:
            raise UploadError(f"Contract Semantic Error: [{e.code}] {e.message}")

        # 3. Extract trace if it's a bag/db3
        jsonl_trace_path = trace_path
        if original_ext in [".bag", ".db3"]:
            jsonl_trace_path = temp_dir / "trace.jsonl"
            script_path = IG_DIR / "scripts" / "ig_extract_trace.py"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(IG_DIR)
            result = subprocess.run(
                ["python3", str(script_path), "--bag", str(trace_path), "--out", str(jsonl_trace_path)],
                capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                raise UploadError(f"Failed to extract trace from bag: {result.stderr}")
        elif original_ext != ".jsonl":
            raise UploadError(f"Unsupported trace file extension: {original_ext}. Use .jsonl, .bag, or .db3.")

        # Read the jsonl trace to get raw events
        raw_events = []
        with open(jsonl_trace_path, "r") as f:
            for line in f:
                if line.strip():
                    raw_events.append(json.loads(line))

        if not raw_events:
            raise UploadError("Trace is empty.")

        # 4. Audit Trace
        audit_script = IG_DIR / "src" / "cli" / "audit.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(IG_DIR)
        result = subprocess.run(
            ["python3", str(audit_script), "--contract", str(contract_path), "--trace", str(jsonl_trace_path)],
            capture_output=True, text=True, env=env
        )
        
        # The auditor exits with 0 for PASS, 1 for FAIL. Both print valid JSON to stdout.
        # If stdout is empty or not JSON, it's a real crash.
        try:
            raw_audit = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise UploadError(f"Auditor failed to run. Stderr: {result.stderr}\nStdout: {result.stdout}")

        # 5. Transform and save
        contract_id_name = contract_file.filename if contract_file else "manual_contract.ig.json"
        scenario_pkg = audit_mapper.transform_scenario(
            scenario_id=scenario_id,
            contract_id=contract_id_name,
            raw_trace_events=raw_events,
            raw_audit=raw_audit,
            interaction_type=interaction_type,
            robot_platform=robot_platform,
            source_bag=trace_file.filename if original_ext in [".bag", ".db3"] else None,
        )

        target_dir = get_dataset_root() / scenario_id
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        (target_dir / "traces").mkdir(parents=True)
        (target_dir / "contracts").mkdir(parents=True)
        (target_dir / "audits").mkdir(parents=True)

        with open(target_dir / "metadata.yaml", "w") as f:
            f.write(scenario_pkg["metadata.yaml"])
        
        with open(target_dir / "contracts" / "contract.ig.json", "w") as f:
            json.dump(contract_data, f, indent=2)

        with open(target_dir / "traces" / "trace.json", "w") as f:
            json.dump(scenario_pkg["trace.json"], f, indent=2)

        with open(target_dir / "audits" / "audit_report.json", "w") as f:
            json.dump(scenario_pkg["audit_report.json"], f, indent=2)

        if scenario_pkg["counterexample.json"]:
            with open(target_dir / "audits" / "counterexample.json", "w") as f:
                json.dump(scenario_pkg["counterexample.json"], f, indent=2)

        return {"scenario_id": scenario_id, "status": "success"}

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
