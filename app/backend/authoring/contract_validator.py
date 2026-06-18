"""
Module G: Contract Validator Adapter

Responsibility: Wrap existing Phase 5 validators to validate generated contracts.
Does NOT duplicate validation logic — calls existing SchemaValidator,
ContractParser, and SemanticValidator.

Pass conditions (from PRD):
  • Valid generated contract passes.
  • Invalid generated contract fails.
  • Missing repair site fails.
  • Invalid latency expression fails.
  • Error messages are returned to frontend.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any

from authoring.schemas import ValidationResult

logger = logging.getLogger(__name__)

# Add interaction-grammar to import path
_IG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "interaction-grammar"
if str(_IG_DIR) not in sys.path:
    sys.path.insert(0, str(_IG_DIR))

try:
    from src.compiler.validator import (
        SchemaValidator,
        SemanticValidator,
        ValidationError,
        prepare_contract_for_validation,
    )
    from src.compiler.parser import ContractParser, ParserError
    from src.compiler.constraint_parser import ConstraintError
    from jsonschema import ValidationError as JsonSchemaError
    _VALIDATORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import interaction-grammar validators: {e}")
    _VALIDATORS_AVAILABLE = False


def validate_contract(contract_json: Dict[str, Any]) -> ValidationResult:
    """
    Run existing Phase 5 validators on a generated contract.

    Steps:
      1. Schema validation (schema.json)
      2. AST parsing (ContractParser)
      3. Semantic validation (SemanticValidator)

    Returns:
      ValidationResult with per-stage pass/fail and error details.
    """
    result = ValidationResult()

    if not _VALIDATORS_AVAILABLE:
        result.errors.append("Validators not available (import failed)")
        return result

    schema_path = _IG_DIR / "schema" / "schema.json"

    contract_for_validation = dict(contract_json)
    prepare_contract_for_validation(contract_for_validation)

    # 1. Schema validation
    try:
        sv = SchemaValidator(str(schema_path))
        sv.validate(contract_for_validation)
        result.schema_valid = True
        logger.info("Schema validation: PASSED")
    except JsonSchemaError as e:
        result.errors.append(f"Schema error: {e.message}")
        logger.warning(f"Schema validation: FAILED — {e.message}")
    except Exception as e:
        result.errors.append(f"Schema error: {str(e)}")
        logger.warning(f"Schema validation: FAILED — {e}")

    # 2. AST parsing + repair sites
    ast = None
    try:
        parser = ContractParser()
        ast = parser.parse(contract_for_validation)
        result.repair_sites_valid = True  # Parsing succeeded = sites are valid
        logger.info("AST parsing: PASSED")
    except ParserError as e:
        result.errors.append(f"Parse error [{e.code}]: {e.message}")
        logger.warning(f"AST parsing: FAILED — [{e.code}] {e.message}")
    except ConstraintError as e:
        result.errors.append(f"Constraint error [{e.code}]: {e.message}")
        logger.warning(f"Constraint parsing: FAILED — [{e.code}] {e.message}")
    except Exception as e:
        result.errors.append(f"Parse error: {str(e)}")
        logger.warning(f"AST parsing: FAILED — {e}")

    # 3. Semantic validation
    if ast is not None:
        try:
            sem = SemanticValidator()
            sem.validate(ast)
            result.semantic_valid = True
            logger.info("Semantic validation: PASSED")
        except ValidationError as e:
            result.errors.append(f"Semantic error [{e.code}]: {e.message}")
            logger.warning(f"Semantic validation: FAILED — [{e.code}] {e.message}")
        except Exception as e:
            result.errors.append(f"Semantic error: {str(e)}")
            logger.warning(f"Semantic validation: FAILED — {e}")
    else:
        result.warnings.append("Semantic validation skipped (AST parsing failed)")

    return result
