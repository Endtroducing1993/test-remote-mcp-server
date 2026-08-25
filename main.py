from fastmcp import FastMCP
import random

mcp = FastMCP("Random Number Server")


@mcp.tool()
def random_number(min_value: int = 0, max_value: int = 100) -> int:
    """
    Generate a random integer between min_value and max_value.

    Args:
        min_value: Minimum value (default: 0)
        max_value: Maximum value (default: 100)

    Returns:
        A random integer between the given values.
    """
    if min_value > max_value:
        raise ValueError("min_value cannot be greater than max_value")

    return random.randint(min_value, max_value)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)