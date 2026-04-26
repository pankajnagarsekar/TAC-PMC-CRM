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
            try:
                result[key] = float(value.to_decimal())
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
            result[key] = [
                serialize_doc(item) if isinstance(item, dict)
                else float(item) if isinstance(item, Decimal)
                else str(item) if isinstance(item, (ObjectId, datetime))
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def prepare_for_db(data: Any) -> Any:
    """
    Recursively convert Decimal to float for MongoDB storage.
    Ensures datetimes are offset-aware if they aren't.
    """
    from datetime import timezone
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, datetime):
        if data.tzinfo is None:
            return data.replace(tzinfo=timezone.utc)
        return data
    if isinstance(data, dict):
        return {k: prepare_for_db(v) for k, v in data.items()}
    if isinstance(data, list):
        return [prepare_for_db(i) for i in data]
    return data


def serialize_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs if doc is not None]
