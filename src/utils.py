from typing import Union

JsonType = Union[dict[str, "JsonType"], list["JsonType"], str, int, float, bool, None]
