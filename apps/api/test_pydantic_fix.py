from bson import ObjectId
from pydantic_core import core_schema


def test_pydantic_fix():
    try:
        core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.wrap_serializer_function_ser_schema(
                lambda v, h: str(v) if isinstance(v, ObjectId) else h(v),
                schema=core_schema.str_schema(),
            ),
        )
        print("Success: wrap_serializer_function_ser_schema works")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_pydantic_fix()
