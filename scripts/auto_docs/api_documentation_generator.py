#!/usr/bin/env python3
"""
API Documentation Generator for Alice v2

Automatically generates comprehensive API documentation by analyzing FastAPI applications,
extracting docstrings, type hints, and route definitions. Creates both OpenAPI specs
and human-readable markdown documentation.

Features:
- Automatic endpoint discovery from FastAPI routers
- Type hint analysis for request/response models
- Docstring extraction and formatting
- OpenAPI specification generation
- Interactive API documentation
- Code example generation
- Error code documentation
"""

import ast
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# FastAPI imports (if available)
try:
    import fastapi  # noqa: F401
    import pydantic  # noqa: F401

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class APIEndpoint:
    """Represents a single API endpoint."""

    path: str
    method: str
    name: str
    description: str
    summary: str
    tags: List[str]
    request_model: Optional[str] = None
    response_model: Optional[str] = None
    parameters: List[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = None
    examples: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}
        if self.examples is None:
            self.examples = []


@dataclass
class APIService:
    """Represents a service with its API endpoints."""

    name: str
    description: str
    version: str
    base_path: str
    endpoints: List[APIEndpoint]
    models: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.models is None:
            self.models = {}


class APIDocumentationGenerator:
    """Generates comprehensive API documentation for Alice v2 services."""

    def __init__(self, project_root: Path):
        """Initialize the API documentation generator."""
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "services"
        self.docs_dir = self.project_root / "docs" / "api"
        self.logger = structlog.get_logger(__name__)

        # Ensure docs directory exists
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self.discovered_services: List[APIService] = []

    def discover_services(self) -> List[APIService]:
        """Discover all services with FastAPI applications."""
        services = []

        if not FASTAPI_AVAILABLE:
            self.logger.warning("FastAPI not available, skipping API discovery")
            return services

        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue

            service_name = service_dir.name
            main_file = service_dir / "main.py"

            if not main_file.exists():
                continue

            try:
                service = self._analyze_service(service_name, service_dir)
                if service:
                    services.append(service)
                    self.logger.info(
                        "Discovered service",
                        name=service_name,
                        endpoints=len(service.endpoints),
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to analyze service", service=service_name, error=str(e)
                )

        self.discovered_services = services
        return services

    def _analyze_service(
        self, service_name: str, service_dir: Path
    ) -> Optional[APIService]:
        """Analyze a single service to extract API information."""
        main_file = service_dir / "main.py"

        # Read and parse the main.py file
        try:
            with open(main_file, "r") as f:
                content = f.read()
        except Exception as e:
            self.logger.error(
                "Failed to read main.py", service=service_name, error=str(e)
            )
            return None

        # Parse AST to find FastAPI app and routers
        try:
            tree = ast.parse(content, filename=str(main_file))
        except Exception as e:
            self.logger.error(
                "Failed to parse main.py", service=service_name, error=str(e)
            )
            return None

        # Try to dynamically import and analyze
        try:
            # Add service directory to Python path temporarily
            sys.path.insert(0, str(service_dir.parent))

            # Import the main module
            # Don't execute the module (might start servers), just analyze statically
            endpoints = self._extract_endpoints_from_ast(tree, service_dir)
            models = self._extract_models_from_directory(service_dir)

            service = APIService(
                name=service_name,
                description=self._extract_service_description(tree),
                version=self._extract_service_version(service_dir),
                base_path=f"/{service_name}" if service_name != "orchestrator" else "",
                endpoints=endpoints,
                models=models,
            )

            return service

        except Exception as e:
            self.logger.error(
                "Failed to analyze service dynamically",
                service=service_name,
                error=str(e),
            )
            return None
        finally:
            # Remove from path
            if str(service_dir.parent) in sys.path:
                sys.path.remove(str(service_dir.parent))

    def _extract_endpoints_from_ast(
        self, tree: ast.AST, service_dir: Path
    ) -> List[APIEndpoint]:
        """Extract API endpoints by analyzing AST and router files."""
        endpoints = []

        # Look for router files in src/routers/
        routers_dir = service_dir / "src" / "routers"
        if routers_dir.exists():
            for router_file in routers_dir.glob("*.py"):
                if router_file.name == "__init__.py":
                    continue

                try:
                    router_endpoints = self._analyze_router_file(router_file)
                    endpoints.extend(router_endpoints)
                except Exception as e:
                    self.logger.warning(
                        "Failed to analyze router", file=str(router_file), error=str(e)
                    )

        return endpoints

    def _analyze_router_file(self, router_file: Path) -> List[APIEndpoint]:
        """Analyze a single router file to extract endpoints."""
        endpoints = []

        try:
            with open(router_file, "r") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(router_file))

            # Find function definitions with route decorators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint = self._extract_endpoint_from_function(node, router_file)
                    if endpoint:
                        endpoints.append(endpoint)

        except Exception as e:
            self.logger.error(
                "Failed to analyze router file", file=str(router_file), error=str(e)
            )

        return endpoints

    def _extract_endpoint_from_function(
        self, func_node: ast.FunctionDef, router_file: Path
    ) -> Optional[APIEndpoint]:
        """Extract endpoint information from a function definition."""
        # Look for route decorators
        route_info = None

        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                # router.post(), router.get(), etc.
                if hasattr(decorator, "attr") and decorator.attr in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                ]:
                    method = decorator.attr.upper()

                    # Try to extract path from decorator arguments
                    path = "/"
                    if hasattr(decorator, "args") and len(decorator.args) > 0:
                        if isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value

                    route_info = (method, path)
                    break

            elif isinstance(decorator, ast.Call):
                # @router.post("/path")
                if isinstance(
                    decorator.func, ast.Attribute
                ) and decorator.func.attr in ["get", "post", "put", "delete", "patch"]:
                    method = decorator.func.attr.upper()

                    path = "/"
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value

                    route_info = (method, path)
                    break

        if not route_info:
            return None

        method, path = route_info

        # Extract function information
        description = ""
        summary = func_node.name.replace("_", " ").title()

        # Extract docstring
        if (
            func_node.body
            and isinstance(func_node.body[0], ast.Expr)
            and isinstance(func_node.body[0].value, ast.Constant)
        ):
            description = func_node.body[0].value.value

        # Extract parameters from function signature
        parameters = []
        for arg in func_node.args.args:
            if arg.arg not in ["request", "response"]:  # Skip FastAPI injected params
                param = {
                    "name": arg.arg,
                    "type": "string",  # Default, would need type annotation analysis
                    "required": True,
                    "description": f"Parameter {arg.arg}",
                }
                parameters.append(param)

        endpoint = APIEndpoint(
            path=path,
            method=method,
            name=func_node.name,
            description=description,
            summary=summary,
            tags=[router_file.stem],  # Use router filename as tag
            parameters=parameters,
        )

        return endpoint

    def _extract_models_from_directory(
        self, service_dir: Path
    ) -> Dict[str, Dict[str, Any]]:
        """Extract Pydantic models from service directory."""
        models = {}

        # Look for models in src/models/
        models_dir = service_dir / "src" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.py"):
                if model_file.name == "__init__.py":
                    continue

                try:
                    file_models = self._extract_models_from_file(model_file)
                    models.update(file_models)
                except Exception as e:
                    self.logger.warning(
                        "Failed to extract models", file=str(model_file), error=str(e)
                    )

        return models

    def _extract_models_from_file(self, model_file: Path) -> Dict[str, Dict[str, Any]]:
        """Extract Pydantic models from a Python file."""
        models = {}

        try:
            with open(model_file, "r") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(model_file))

            # Find class definitions that inherit from BaseModel
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits from BaseModel
                    is_pydantic_model = False
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseModel":
                            is_pydantic_model = True
                            break

                    if is_pydantic_model:
                        model_info = self._extract_model_info(node)
                        models[node.name] = model_info

        except Exception as e:
            self.logger.error(
                "Failed to extract models from file", file=str(model_file), error=str(e)
            )

        return models

    def _extract_model_info(self, class_node: ast.ClassDef) -> Dict[str, Any]:
        """Extract information from a Pydantic model class."""
        model_info = {
            "name": class_node.name,
            "description": "",
            "properties": {},
            "required": [],
        }

        # Extract docstring
        if (
            class_node.body
            and isinstance(class_node.body[0], ast.Expr)
            and isinstance(class_node.body[0].value, ast.Constant)
        ):
            model_info["description"] = class_node.body[0].value.value

        # Extract field definitions
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                field_name = node.target.id
                field_type = self._ast_to_type_string(node.annotation)

                property_info = {
                    "type": field_type,
                    "description": f"Field {field_name}",
                }

                # Check if field has default value
                if node.value is None:
                    model_info["required"].append(field_name)

                model_info["properties"][field_name] = property_info

        return model_info

    def _ast_to_type_string(self, annotation: ast.AST) -> str:
        """Convert AST annotation to type string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            if isinstance(annotation.value, ast.Name):
                base_type = annotation.value.id
                if isinstance(annotation.slice, ast.Name):
                    return f"{base_type}[{annotation.slice.id}]"
                elif isinstance(annotation.slice, ast.Tuple):
                    args = [
                        self._ast_to_type_string(elt) for elt in annotation.slice.elts
                    ]
                    return f"{base_type}[{', '.join(args)}]"

        return "Any"

    def _extract_service_description(self, tree: ast.AST) -> str:
        """Extract service description from module docstring."""
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
        ):
            return tree.body[0].value.value
        return ""

    def _extract_service_version(self, service_dir: Path) -> str:
        """Extract service version from various sources."""
        # Try pyproject.toml
        pyproject_file = service_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import toml

                pyproject = toml.load(pyproject_file)
                return (
                    pyproject.get("tool", {}).get("poetry", {}).get("version", "1.0.0")
                )
            except Exception:
                pass

        # Try requirements.txt or other version indicators
        return "1.0.0"

    def generate_openapi_spec(self, service: APIService) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification for a service."""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": f"{service.name.title()} API",
                "description": service.description or f"API for {service.name} service",
                "version": service.version,
                "contact": {
                    "name": "Alice v2 Team",
                    "url": "https://github.com/alice-v2",
                },
            },
            "servers": [
                {
                    "url": f"http://localhost:8000{service.base_path}",
                    "description": "Development server",
                },
                {
                    "url": f"http://localhost:18000{service.base_path}",
                    "description": "API Gateway",
                },
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {"type": "http", "scheme": "bearer"},
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                },
            },
        }

        # Add paths
        for endpoint in service.endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}

            spec["paths"][endpoint.path][endpoint.method.lower()] = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "operationId": f"{endpoint.method.lower()}_{endpoint.name}",
                "parameters": [
                    {
                        "name": param["name"],
                        "in": "query" if endpoint.method == "GET" else "body",
                        "required": param["required"],
                        "schema": {"type": param["type"]},
                        "description": param["description"],
                    }
                    for param in endpoint.parameters
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "400": {"description": "Bad request"},
                    "500": {"description": "Internal server error"},
                },
                "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
            }

        # Add schemas
        for model_name, model_info in service.models.items():
            spec["components"]["schemas"][model_name] = {
                "type": "object",
                "description": model_info["description"],
                "properties": model_info["properties"],
                "required": model_info["required"],
            }

        return spec

    def generate_markdown_docs(self, service: APIService) -> str:
        """Generate markdown documentation for a service."""
        lines = [
            f"# {service.name.title()} API Documentation",
            "",
            f"**Version:** {service.version}  ",
            f"**Base Path:** `{service.base_path or '/'}`  ",
            "",
            "## Overview",
            "",
            service.description or f"API documentation for the {service.name} service.",
            "",
            "## Authentication",
            "",
            "This API supports two authentication methods:",
            "",
            "- **Bearer Token**: Include `Authorization: Bearer <token>` header",
            "- **API Key**: Include `X-API-Key: <key>` header",
            "",
            "## Endpoints",
            "",
        ]

        # Group endpoints by tag
        endpoints_by_tag = {}
        for endpoint in service.endpoints:
            tag = endpoint.tags[0] if endpoint.tags else "default"
            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []
            endpoints_by_tag[tag].append(endpoint)

        # Generate documentation for each tag
        for tag, endpoints in endpoints_by_tag.items():
            lines.extend([f"### {tag.title()}", ""])

            for endpoint in endpoints:
                lines.extend(
                    [
                        f"#### `{endpoint.method} {endpoint.path}`",
                        "",
                        endpoint.description or endpoint.summary,
                        "",
                        "**Parameters:**",
                        "",
                    ]
                )

                if endpoint.parameters:
                    lines.append("| Name | Type | Required | Description |")
                    lines.append("|------|------|----------|-------------|")
                    for param in endpoint.parameters:
                        required = "✓" if param["required"] else "-"
                        lines.append(
                            f"| `{param['name']}` | {param['type']} | {required} | {param['description']} |"
                        )
                else:
                    lines.append("No parameters required.")

                lines.extend(["", "**Example Request:**", "", "```bash"])

                # Generate curl example
                if endpoint.method == "GET":
                    lines.append("curl -H 'Authorization: Bearer <token>' \\")
                    lines.append(
                        f"     http://localhost:8000{service.base_path}{endpoint.path}"
                    )
                else:
                    lines.append(f"curl -X {endpoint.method} \\")
                    lines.append("     -H 'Authorization: Bearer <token>' \\")
                    lines.append("     -H 'Content-Type: application/json' \\")
                    if endpoint.parameters:
                        lines.append('     -d \'{"example": "data"}\' \\')
                    lines.append(
                        f"     http://localhost:8000{service.base_path}{endpoint.path}"
                    )

                lines.extend(
                    [
                        "```",
                        "",
                        "**Example Response:**",
                        "",
                        "```json",
                        "{",
                        '  "status": "success",',
                        '  "data": {}',
                        "}",
                        "```",
                        "",
                        "---",
                        "",
                    ]
                )

        # Add models section if any
        if service.models:
            lines.extend(["## Data Models", ""])

            for model_name, model_info in service.models.items():
                lines.extend(
                    [
                        f"### {model_name}",
                        "",
                        model_info["description"],
                        "",
                        "**Properties:**",
                        "",
                    ]
                )

                if model_info["properties"]:
                    lines.append("| Name | Type | Required | Description |")
                    lines.append("|------|------|----------|-------------|")
                    for prop_name, prop_info in model_info["properties"].items():
                        required = "✓" if prop_name in model_info["required"] else "-"
                        lines.append(
                            f"| `{prop_name}` | {prop_info['type']} | {required} | {prop_info['description']} |"
                        )

                lines.extend(["", ""])

        # Add error codes section
        lines.extend(
            [
                "## Error Codes",
                "",
                "| Code | Description |",
                "|------|-------------|",
                "| 200 | Success |",
                "| 400 | Bad Request - Invalid parameters |",
                "| 401 | Unauthorized - Invalid or missing authentication |",
                "| 403 | Forbidden - Insufficient permissions |",
                "| 404 | Not Found - Resource not found |",
                "| 422 | Validation Error - Invalid request data |",
                "| 429 | Rate Limited - Too many requests |",
                "| 500 | Internal Server Error |",
                "| 503 | Service Unavailable - System overloaded |",
                "",
                "---",
                "",
                f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Alice v2 API Documentation Generator*",
            ]
        )

        return "\n".join(lines)

    def generate_all_documentation(self):
        """Generate documentation for all discovered services."""
        self.logger.info("Starting API documentation generation")

        # Discover services
        services = self.discover_services()

        if not services:
            self.logger.warning("No services discovered")
            return

        # Generate documentation for each service
        for service in services:
            self.logger.info("Generating documentation", service=service.name)

            try:
                # Generate OpenAPI spec
                openapi_spec = self.generate_openapi_spec(service)
                openapi_file = self.docs_dir / f"{service.name}_openapi.json"

                with open(openapi_file, "w") as f:
                    json.dump(openapi_spec, f, indent=2)

                # Generate markdown documentation
                markdown_docs = self.generate_markdown_docs(service)
                markdown_file = self.docs_dir / f"{service.name}_api.md"

                with open(markdown_file, "w") as f:
                    f.write(markdown_docs)

                self.logger.info(
                    "Generated documentation",
                    service=service.name,
                    endpoints=len(service.endpoints),
                    models=len(service.models),
                )

            except Exception as e:
                self.logger.error(
                    "Failed to generate documentation",
                    service=service.name,
                    error=str(e),
                )

        # Generate index file
        self._generate_api_index(services)

        self.logger.info(
            "API documentation generation completed", services=len(services)
        )

    def _generate_api_index(self, services: List[APIService]):
        """Generate an index file for all API documentation."""
        lines = [
            "# Alice v2 API Documentation",
            "",
            "Complete API documentation for all Alice v2 services.",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Services:** {len(services)}  ",
            "",
            "## Services",
            "",
        ]

        for service in services:
            lines.extend(
                [
                    f"### {service.name.title()}",
                    "",
                    service.description or f"API for {service.name} service",
                    "",
                    f"- **Documentation:** [{service.name}_api.md]({service.name}_api.md)",
                    f"- **OpenAPI Spec:** [{service.name}_openapi.json]({service.name}_openapi.json)",
                    f"- **Endpoints:** {len(service.endpoints)}",
                    f"- **Models:** {len(service.models)}",
                    "",
                ]
            )

        lines.extend(
            [
                "## Quick Start",
                "",
                "1. **Authentication**: Obtain API key or JWT token",
                "2. **Base URL**: Use `http://localhost:18000` for API gateway",
                "3. **Headers**: Include authentication headers with requests",
                "4. **Format**: All requests/responses use JSON format",
                "",
                "## Common Patterns",
                "",
                "### Authentication",
                "",
                "```bash",
                "# Using Bearer token",
                "curl -H 'Authorization: Bearer <token>' http://localhost:18000/api/endpoint",
                "",
                "# Using API key",
                "curl -H 'X-API-Key: <key>' http://localhost:18000/api/endpoint",
                "```",
                "",
                "### Error Handling",
                "",
                "All APIs return consistent error responses:",
                "",
                "```json",
                "{",
                '  "error": {',
                '    "code": "VALIDATION_ERROR",',
                '    "message": "Invalid request parameters",',
                '    "details": {}',
                "  }",
                "}",
                "```",
                "",
            ]
        )

        index_file = self.docs_dir / "README.md"
        with open(index_file, "w") as f:
            f.write("\n".join(lines))


def main():
    """Main entry point for the API documentation generator."""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        project_root = Path(__file__).parent.parent.parent

    generator = APIDocumentationGenerator(project_root)
    generator.generate_all_documentation()


if __name__ == "__main__":
    main()
