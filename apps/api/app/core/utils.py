from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId, Decimal128
from decimal import Decimal

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Recursively serialize MongoDB documents for JSON responses.
    Fixed CR-19: Does NOT convert Decimal to float. Uses str for precision.
    """
    if doc is None:
        return None
        
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, Decimal128):
            # FIXED: Avoid float() precision loss. Use string representation.
            result[key] = str(value.to_decimal())
        elif isinstance(value, Decimal):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(item) if isinstance(item, dict)
                else str(item.to_decimal()) if isinstance(item, Decimal128)
                else str(item) if isinstance(item, (Decimal, ObjectId))
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result

def serialize_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs if doc is not None]
