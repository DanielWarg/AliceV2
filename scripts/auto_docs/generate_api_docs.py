#!/usr/bin/env python3
"""
API Documentation Generator
Automatically generates and updates API documentation from code.
"""

import ast
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class APIDocGenerator:
    """Generates API documentation from Python source code."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "services"
        self.docs_api_dir = self.project_root / "docs" / "api"
        self.docs_api_dir.mkdir(parents=True, exist_ok=True)

    def extract_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from an AST node."""
        if (
            isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            return node.body[0].value.value
        return None

    def extract_function_info(self, node: ast.FunctionDef) -> Dict:
        """Extract information from a function definition."""
        info = {
            "name": node.name,
            "docstring": self.extract_docstring(node),
            "args": [],
            "returns": None,
            "decorators": [],
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        }

        # Extract arguments
        for arg in node.args.args:
            arg_info = {"name": arg.arg, "annotation": None, "default": None}
            if arg.annotation:
                arg_info["annotation"] = ast.unparse(arg.annotation)
            info["args"].append(arg_info)

        # Extract defaults
        defaults = node.args.defaults
        if defaults:
            num_defaults = len(defaults)
            for i, default in enumerate(defaults):
                arg_idx = len(info["args"]) - num_defaults + i
                if arg_idx >= 0:
                    info["args"][arg_idx]["default"] = ast.unparse(default)

        # Extract return annotation
        if node.returns:
            info["returns"] = ast.unparse(node.returns)

        # Extract decorators
        for decorator in node.decorator_list:
            info["decorators"].append(ast.unparse(decorator))

        return info

    def extract_class_info(self, node: ast.ClassDef) -> Dict:
        """Extract information from a class definition."""
        info = {
            "name": node.name,
            "docstring": self.extract_docstring(node),
            "bases": [ast.unparse(base) for base in node.bases],
            "methods": [],
            "attributes": [],
            "decorators": [],
        }

        # Extract methods and attributes
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self.extract_function_info(child)
                method_info["is_method"] = True
                method_info["visibility"] = self.get_visibility(child.name)
                info["methods"].append(method_info)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        attr_info = {
                            "name": target.id,
                            "value": ast.unparse(child.value),
                            "visibility": self.get_visibility(target.id),
                        }
                        info["attributes"].append(attr_info)

        # Extract decorators
        for decorator in node.decorator_list:
            info["decorators"].append(ast.unparse(decorator))

        return info

    def get_visibility(self, name: str) -> str:
        """Determine the visibility of a name (public, protected, private)."""
        if name.startswith("__") and name.endswith("__"):
            return "magic"
        elif name.startswith("__"):
            return "private"
        elif name.startswith("_"):
            return "protected"
        else:
            return "public"

    def analyze_python_file(self, file_path: Path) -> Dict:
        """Analyze a Python file and extract API information."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                "file_path": str(file_path.relative_to(self.project_root)),
                "module_docstring": self.extract_docstring(tree),
                "functions": [],
                "classes": [],
                "imports": [],
                "constants": [],
            }

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only include top-level functions (not methods)
                    if isinstance(
                        node.parent if hasattr(node, "parent") else None, ast.Module
                    ):
                        func_info = self.extract_function_info(node)
                        func_info["visibility"] = self.get_visibility(node.name)
                        info["functions"].append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info = self.extract_class_info(node)
                    class_info["visibility"] = self.get_visibility(node.name)
                    info["classes"].append(class_info)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = {"type": type(node).__name__}
                    if isinstance(node, ast.Import):
                        import_info["modules"] = [alias.name for alias in node.names]
                    else:  # ImportFrom
                        import_info["module"] = node.module
                        import_info["names"] = [alias.name for alias in node.names]
                    info["imports"].append(import_info)

                elif isinstance(node, ast.Assign):
                    # Only include module-level constants
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            const_info = {
                                "name": target.id,
                                "value": ast.unparse(node.value),
                                "type": type(
                                    ast.literal_eval(node.value)
                                    if self.is_literal(node.value)
                                    else None
                                ).__name__,
                            }
                            info["constants"].append(const_info)

            return info

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                "file_path": str(file_path.relative_to(self.project_root)),
                "error": str(e),
                "functions": [],
                "classes": [],
                "imports": [],
                "constants": [],
            }

    def is_literal(self, node: ast.AST) -> bool:
        """Check if a node represents a literal value."""
        try:
            ast.literal_eval(node)
            return True
        except (ValueError, TypeError):
            return False

    def generate_markdown_docs(self, api_info: Dict, service_name: str) -> str:
        """Generate markdown documentation from API information."""
        md = f"# {service_name.title()} API Documentation\n\n"
        md += (
            f"Auto-generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        )

        if api_info.get("module_docstring"):
            md += f"## Overview\n\n{api_info['module_docstring']}\n\n"

        # Constants
        if api_info.get("constants"):
            md += "## Constants\n\n"
            md += "| Name | Value | Type |\n|------|-------|------|\n"
            for const in api_info["constants"]:
                value = const["value"]
                if len(value) > 50:
                    value = value[:47] + "..."
                md += f"| `{const['name']}` | `{value}` | {const.get('type', 'Unknown')} |\n"
            md += "\n"

        # Functions
        if api_info.get("functions"):
            md += "## Functions\n\n"
            for func in api_info["functions"]:
                if func["visibility"] != "public":
                    continue  # Skip private/protected functions in public docs

                md += f"### `{func['name']}`\n\n"

                if func.get("docstring"):
                    md += f"{func['docstring']}\n\n"

                # Function signature
                args_str = []
                for arg in func["args"]:
                    arg_str = arg["name"]
                    if arg.get("annotation"):
                        arg_str += f": {arg['annotation']}"
                    if arg.get("default"):
                        arg_str += f" = {arg['default']}"
                    args_str.append(arg_str)

                signature = f"{'async ' if func['is_async'] else ''}{func['name']}({', '.join(args_str)})"
                if func.get("returns"):
                    signature += f" -> {func['returns']}"

                md += f"```python\n{signature}\n```\n\n"

                # Decorators
                if func.get("decorators"):
                    md += f"**Decorators:** {', '.join(func['decorators'])}\n\n"

        # Classes
        if api_info.get("classes"):
            md += "## Classes\n\n"
            for cls in api_info["classes"]:
                if cls["visibility"] != "public":
                    continue

                md += f"### `{cls['name']}`\n\n"

                if cls.get("docstring"):
                    md += f"{cls['docstring']}\n\n"

                if cls.get("bases"):
                    md += f"**Inherits from:** {', '.join(cls['bases'])}\n\n"

                # Public methods
                public_methods = [
                    m for m in cls["methods"] if m["visibility"] == "public"
                ]
                if public_methods:
                    md += "#### Methods\n\n"
                    for method in public_methods:
                        md += f"##### `{method['name']}`\n\n"

                        if method.get("docstring"):
                            md += f"{method['docstring']}\n\n"

                        # Method signature
                        args_str = []
                        for arg in method["args"]:
                            arg_str = arg["name"]
                            if arg.get("annotation"):
                                arg_str += f": {arg['annotation']}"
                            if arg.get("default"):
                                arg_str += f" = {arg['default']}"
                            args_str.append(arg_str)

                        signature = f"{'async ' if method['is_async'] else ''}{method['name']}({', '.join(args_str)})"
                        if method.get("returns"):
                            signature += f" -> {method['returns']}"

                        md += f"```python\n{signature}\n```\n\n"

                # Public attributes
                public_attrs = [
                    a for a in cls["attributes"] if a["visibility"] == "public"
                ]
                if public_attrs:
                    md += "#### Attributes\n\n"
                    md += "| Name | Value |\n|------|-------|\n"
                    for attr in public_attrs:
                        value = attr["value"]
                        if len(value) > 50:
                            value = value[:47] + "..."
                        md += f"| `{attr['name']}` | `{value}` |\n"
                    md += "\n"

        return md

    def scan_service_apis(self) -> Dict[str, List[Dict]]:
        """Scan all services for API endpoints and documentation."""
        services_info = {}

        if not self.services_dir.exists():
            print(f"Services directory not found: {self.services_dir}")
            return services_info

        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir() or service_dir.name.startswith("."):
                continue

            service_name = service_dir.name
            print(f"Scanning service: {service_name}")

            # Find Python files in the service
            python_files = []
            for root, dirs, files in os.walk(service_dir):
                # Skip hidden directories and __pycache__
                dirs[:] = [
                    d for d in dirs if not d.startswith(".") and d != "__pycache__"
                ]

                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        python_files.append(Path(root) / file)

            service_apis = []
            for py_file in python_files:
                api_info = self.analyze_python_file(py_file)
                if api_info.get("functions") or api_info.get("classes"):
                    service_apis.append(api_info)

            services_info[service_name] = service_apis

        return services_info

    def generate_service_docs(self, service_name: str, service_apis: List[Dict]) -> str:
        """Generate documentation for a specific service."""
        md = f"# {service_name.title()} Service API\n\n"
        md += f"Auto-generated API documentation for the {service_name} service.\n\n"
        md += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

        md += "## Service Modules\n\n"

        for api_info in service_apis:
            if api_info.get("error"):
                md += f"### ⚠️ {api_info['file_path']}\n\n"
                md += f"Error analyzing file: {api_info['error']}\n\n"
                continue

            file_name = Path(api_info["file_path"]).name
            module_name = file_name.replace(".py", "")

            md += f"### {module_name}\n\n"
            md += f"**File:** `{api_info['file_path']}`\n\n"

            if api_info.get("module_docstring"):
                md += f"{api_info['module_docstring']}\n\n"

            # Quick summary
            summary_parts = []
            if api_info.get("functions"):
                public_funcs = [
                    f for f in api_info["functions"] if f["visibility"] == "public"
                ]
                if public_funcs:
                    summary_parts.append(f"{len(public_funcs)} public functions")

            if api_info.get("classes"):
                public_classes = [
                    c for c in api_info["classes"] if c["visibility"] == "public"
                ]
                if public_classes:
                    summary_parts.append(f"{len(public_classes)} public classes")

            if api_info.get("constants"):
                summary_parts.append(f"{len(api_info['constants'])} constants")

            if summary_parts:
                md += f"**Contains:** {', '.join(summary_parts)}\n\n"

            # Generate detailed docs for this module
            module_docs = self.generate_markdown_docs(
                api_info, f"{service_name}.{module_name}"
            )
            # Remove the header from module docs since we're embedding it
            module_docs = "\n".join(module_docs.split("\n")[3:])
            md += module_docs

        return md

    def generate_all_docs(self) -> List[str]:
        """Generate documentation for all services."""
        services_info = self.scan_service_apis()
        generated_files = []

        for service_name, service_apis in services_info.items():
            if not service_apis:
                print(f"No API information found for service: {service_name}")
                continue

            docs_content = self.generate_service_docs(service_name, service_apis)

            # Write service documentation
            service_doc_path = self.docs_api_dir / f"{service_name}.md"
            with open(service_doc_path, "w", encoding="utf-8") as f:
                f.write(docs_content)

            generated_files.append(str(service_doc_path))
            print(f"Generated API docs: {service_doc_path}")

        # Generate index
        self.generate_api_index(services_info)
        index_path = self.docs_api_dir / "index.md"
        generated_files.append(str(index_path))

        return generated_files

    def generate_api_index(self, services_info: Dict[str, List[Dict]]) -> None:
        """Generate an index page for all API documentation."""
        md = "# Alice v2 API Documentation\n\n"
        md += "Auto-generated API documentation index.\n\n"
        md += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

        md += "## Available Services\n\n"

        for service_name, service_apis in services_info.items():
            if not service_apis:
                continue

            md += f"### [{service_name.title()} Service]({service_name}.md)\n\n"

            # Count APIs
            total_functions = sum(
                len(
                    [f for f in api.get("functions", []) if f["visibility"] == "public"]
                )
                for api in service_apis
            )
            total_classes = sum(
                len([c for c in api.get("classes", []) if c["visibility"] == "public"])
                for api in service_apis
            )
            total_modules = len(service_apis)

            md += f"- **Modules:** {total_modules}\n"
            md += f"- **Public Functions:** {total_functions}\n"
            md += f"- **Public Classes:** {total_classes}\n\n"

            # List modules
            if service_apis:
                md += "**Modules:**\n"
                for api in service_apis:
                    if api.get("error"):
                        continue
                    file_name = Path(api["file_path"]).name.replace(".py", "")
                    md += f"- `{file_name}`\n"
                md += "\n"

        # Write index
        index_path = self.docs_api_dir / "index.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"Generated API index: {index_path}")


def main():
    """Main execution function."""
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent

    print("API Documentation Generator")
    print(f"Project root: {project_root}")
    print("Scanning services for API documentation...")

    generator = APIDocGenerator(str(project_root))
    generated_files = generator.generate_all_docs()

    if generated_files:
        print(
            f"\nSuccessfully generated {len(generated_files)} API documentation files:"
        )
        for file_path in generated_files:
            print(f"  - {file_path}")
    else:
        print("\nNo API documentation files were generated.")

    return len(generated_files)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(0 if exit_code >= 0 else 1)
