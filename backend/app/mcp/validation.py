"""MCP request validation utilities."""

from typing import Any

from app.mcp.types import MCPErrorCode, MCPToolDefinition, MCPToolParameter


class ValidationError(Exception):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str,
        code: MCPErrorCode = MCPErrorCode.INVALID_PARAMS,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


def validate_param_type(value: Any, param: MCPToolParameter) -> Any:
    """Validate and coerce parameter value to expected type.
    
    Args:
        value: The value to validate
        param: Parameter definition
        
    Returns:
        Coerced value
        
    Raises:
        ValidationError: If value cannot be coerced to expected type
    """
    if value is None:
        if param.required and param.default is None:
            raise ValidationError(
                f"Required parameter '{param.name}' is missing",
                details={"parameter": param.name},
            )
        return param.default

    try:
        if param.type == "string":
            return str(value)
        elif param.type == "integer":
            return int(value)
        elif param.type == "number":
            return float(value)
        elif param.type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        elif param.type == "array":
            if not isinstance(value, list):
                raise ValidationError(
                    f"Parameter '{param.name}' must be an array",
                    details={"parameter": param.name, "expected": "array"},
                )
            return value
        elif param.type == "object":
            if not isinstance(value, dict):
                raise ValidationError(
                    f"Parameter '{param.name}' must be an object",
                    details={"parameter": param.name, "expected": "object"},
                )
            return value
        else:
            return value
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Parameter '{param.name}' has invalid type. Expected {param.type}",
            details={"parameter": param.name, "expected": param.type, "error": str(e)},
        )


def validate_enum(value: Any, param: MCPToolParameter) -> Any:
    """Validate parameter value against enum constraints.
    
    Args:
        value: The value to validate
        param: Parameter definition
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is not in allowed enum values
    """
    if param.enum and value is not None:
        str_value = str(value)
        if str_value not in param.enum:
            raise ValidationError(
                f"Parameter '{param.name}' must be one of: {', '.join(param.enum)}",
                details={
                    "parameter": param.name,
                    "allowed_values": param.enum,
                    "received": str_value,
                },
            )
    return value


def validate_request_params(
    params: dict[str, Any],
    tool_def: MCPToolDefinition,
) -> dict[str, Any]:
    """Validate request parameters against tool definition.
    
    Args:
        params: Request parameters
        tool_def: Tool definition with parameter specs
        
    Returns:
        Validated and coerced parameters
        
    Raises:
        ValidationError: If validation fails
    """
    validated = {}

    # Check for unknown parameters
    known_params = {p.name for p in tool_def.parameters}
    unknown_params = set(params.keys()) - known_params
    if unknown_params:
        # Just ignore unknown params rather than error
        pass

    # Validate each defined parameter
    for param in tool_def.parameters:
        value = params.get(param.name, param.default)

        # Type validation and coercion
        value = validate_param_type(value, param)

        # Enum validation
        value = validate_enum(value, param)

        validated[param.name] = value

    return validated
