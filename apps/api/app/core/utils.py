from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bson import Decimal128, ObjectId


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Authoritative JSON serialization for MongoDB documents (Optimized for Pydantic v2).
    Fixed CR-19: Recursive handling of nested objects, lists, and types.
    """
    if doc is None:
        return None

    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, Decimal128):
            # FIXED: Handle possible to_decimal() failures
            try:
                result[key] = str(value.to_decimal())
            except Exception:
                result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, (Decimal, float)):
            # Keep as float for JSON parity unless Decimal is needed
            result[key] = float(value) if isinstance(value, Decimal) else value
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            serialized_list = []
            for item in value:
                if isinstance(item, dict):
                    serialized_list.append(serialize_doc(item))
                elif isinstance(item, Decimal128):
                    try:
                        serialized_list.append(str(item.to_decimal()))
                    except Exception:
                        serialized_list.append(str(item))
                elif isinstance(item, (Decimal, ObjectId)):
                    serialized_list.append(str(item))
                else:
                    serialized_list.append(item)
            result[key] = serialized_list
        else:
            result[key] = value

    return result


def serialize_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs if doc is not None]
