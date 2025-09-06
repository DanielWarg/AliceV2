#!/usr/bin/env python3
"""
Service Documentation Generator for Alice v2

Automatically generates comprehensive service documentation by analyzing
service directories, Docker configurations, and API definitions.

Features:
- Service discovery from services/ directory
- Docker configuration analysis
- Environment variable documentation
- Health check documentation
- Dependencies and ports analysis
- Deployment configuration
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ServiceDocumentationGenerator:
    """Generates comprehensive service documentation for Alice v2."""

    def __init__(self, project_root: Path):
        """Initialize the service documentation generator."""
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "services"
        self.docs_dir = self.project_root / "docs" / "services"
        self.logger = structlog.get_logger(__name__)

        # Ensure docs directory exists
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self.discovered_services = []

    def discover_services(self) -> List[Dict[str, Any]]:
        """Discover all services in the services directory."""
        services = []

        if not self.services_dir.exists():
            self.logger.warning(
                "Services directory not found", path=str(self.services_dir)
            )
            return services

        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue

            service_name = service_dir.name

            # Skip common non-service directories
            if service_name.startswith(".") or service_name == "__pycache__":
                continue

            try:
                service_info = self._analyze_service(service_name, service_dir)
                if service_info:
                    services.append(service_info)
                    self.logger.info("Discovered service", name=service_name)

            except Exception as e:
                self.logger.error(
                    "Failed to analyze service", service=service_name, error=str(e)
                )

        self.discovered_services = services
        return services

    def _analyze_service(
        self, service_name: str, service_dir: Path
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single service to extract information."""
        service_info = {
            "name": service_name,
            "path": str(service_dir.relative_to(self.project_root)),
            "description": "",
            "version": "1.0.0",
            "type": "unknown",
            "language": "unknown",
            "framework": "unknown",
            "ports": [],
            "environment_variables": [],
            "dependencies": [],
            "health_check": None,
            "dockerfile": None,
            "main_file": None,
            "config_files": [],
            "documentation_files": [],
        }

        # Detect service type and language
        service_info.update(self._detect_service_type(service_dir))

        # Analyze main application file
        service_info["main_file"] = self._find_main_file(service_dir)
        if service_info["main_file"]:
            service_info["description"] = self._extract_service_description(
                service_dir / service_info["main_file"]
            )

        # Analyze Dockerfile
        dockerfile_path = service_dir / "Dockerfile"
        if dockerfile_path.exists():
            service_info["dockerfile"] = self._analyze_dockerfile(dockerfile_path)

        # Analyze configuration files
        service_info["config_files"] = self._find_config_files(service_dir)

        # Extract environment variables
        service_info["environment_variables"] = self._extract_environment_variables(
            service_dir
        )

        # Analyze dependencies
        service_info["dependencies"] = self._analyze_dependencies(service_dir)

        # Find documentation files
        service_info["documentation_files"] = self._find_documentation_files(
            service_dir
        )

        # Extract version
        service_info["version"] = self._extract_version(service_dir)

        return service_info

    def _detect_service_type(self, service_dir: Path) -> Dict[str, Any]:
        """Detect service type, language, and framework."""
        info = {"type": "service", "language": "unknown", "framework": "unknown"}

        # Check for Python services
        if (service_dir / "main.py").exists() or (service_dir / "app.py").exists():
            info["language"] = "python"

            # Check for specific Python frameworks
            if (service_dir / "requirements.txt").exists():
                try:
                    requirements = (service_dir / "requirements.txt").read_text()
                    if "fastapi" in requirements.lower():
                        info["framework"] = "fastapi"
                        info["type"] = "api"
                    elif "flask" in requirements.lower():
                        info["framework"] = "flask"
                        info["type"] = "api"
                    elif "django" in requirements.lower():
                        info["framework"] = "django"
                        info["type"] = "api"
                    elif "streamlit" in requirements.lower():
                        info["framework"] = "streamlit"
                        info["type"] = "dashboard"
                except Exception:
                    pass

        # Check for Node.js services
        elif (service_dir / "package.json").exists():
            info["language"] = "javascript"

            try:
                with open(service_dir / "package.json", "r") as f:
                    package_json = json.load(f)

                dependencies = package_json.get("dependencies", {})
                if "express" in dependencies:
                    info["framework"] = "express"
                    info["type"] = "api"
                elif "next" in dependencies:
                    info["framework"] = "nextjs"
                    info["type"] = "frontend"
                elif "react" in dependencies:
                    info["framework"] = "react"
                    info["type"] = "frontend"

            except Exception:
                pass

        # Check for Go services
        elif (service_dir / "main.go").exists() or (service_dir / "go.mod").exists():
            info["language"] = "go"
            info["framework"] = "go"

        # Check for Rust services
        elif (service_dir / "Cargo.toml").exists():
            info["language"] = "rust"
            info["framework"] = "rust"

        return info

    def _find_main_file(self, service_dir: Path) -> Optional[str]:
        """Find the main application file."""
        candidates = [
            "main.py",
            "app.py",
            "server.py",
            "index.js",
            "app.js",
            "server.js",
            "main.go",
            "main.rs",
        ]

        for candidate in candidates:
            if (service_dir / candidate).exists():
                return candidate

        # Look in src/ directory
        src_dir = service_dir / "src"
        if src_dir.exists():
            for candidate in candidates:
                if (src_dir / candidate).exists():
                    return f"src/{candidate}"

        return None

    def _extract_service_description(self, main_file: Path) -> str:
        """Extract service description from main file."""
        if not main_file.exists():
            return ""

        try:
            content = main_file.read_text()

            # Look for module docstring in Python
            if main_file.suffix == ".py":
                # Find first docstring
                lines = content.split("\n")
                in_docstring = False
                docstring_lines = []

                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        if in_docstring:
                            break
                        in_docstring = True
                        if len(stripped) > 3:
                            docstring_lines.append(stripped[3:])
                        continue

                    if in_docstring:
                        if stripped.endswith('"""') or stripped.endswith("'''"):
                            if len(stripped) > 3:
                                docstring_lines.append(stripped[:-3])
                            break
                        docstring_lines.append(stripped)

                if docstring_lines:
                    return " ".join(docstring_lines).strip()

            # Look for comments at the top
            lines = content.split("\n")
            description_lines = []

            for line in lines[:20]:  # Check first 20 lines
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    comment = stripped[1:].strip()
                    if comment and not comment.startswith("#"):
                        description_lines.append(comment)
                elif (
                    stripped
                    and not stripped.startswith("import")
                    and not stripped.startswith("const")
                ):
                    break

            if description_lines:
                return " ".join(description_lines)

        except Exception as e:
            self.logger.warning(
                "Failed to extract description", file=str(main_file), error=str(e)
            )

        return ""

    def _analyze_dockerfile(self, dockerfile_path: Path) -> Dict[str, Any]:
        """Analyze Dockerfile for service information."""
        dockerfile_info = {
            "base_image": "",
            "exposed_ports": [],
            "environment": [],
            "volumes": [],
            "commands": [],
        }

        try:
            content = dockerfile_path.read_text()
            lines = content.split("\n")

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("FROM"):
                    dockerfile_info["base_image"] = line.split()[1]
                elif line.startswith("EXPOSE"):
                    ports = line.split()[1:]
                    dockerfile_info["exposed_ports"].extend(ports)
                elif line.startswith("ENV"):
                    env_part = " ".join(line.split()[1:])
                    dockerfile_info["environment"].append(env_part)
                elif line.startswith("VOLUME"):
                    volume = " ".join(line.split()[1:])
                    dockerfile_info["volumes"].append(volume)
                elif line.startswith("CMD") or line.startswith("ENTRYPOINT"):
                    dockerfile_info["commands"].append(line)

        except Exception as e:
            self.logger.warning(
                "Failed to analyze Dockerfile", file=str(dockerfile_path), error=str(e)
            )

        return dockerfile_info

    def _find_config_files(self, service_dir: Path) -> List[str]:
        """Find configuration files in service directory."""
        config_files = []

        config_patterns = [
            "*.yml",
            "*.yaml",
            "*.json",
            "*.toml",
            "*.ini",
            "*.conf",
            ".env",
            ".env.*",
            "config.*",
        ]

        for pattern in config_patterns:
            for config_file in service_dir.glob(pattern):
                if config_file.is_file():
                    config_files.append(str(config_file.relative_to(service_dir)))

        # Also check config/ subdirectory
        config_dir = service_dir / "config"
        if config_dir.exists():
            for config_file in config_dir.glob("*"):
                if config_file.is_file():
                    config_files.append(str(config_file.relative_to(service_dir)))

        return sorted(config_files)

    def _extract_environment_variables(self, service_dir: Path) -> List[Dict[str, str]]:
        """Extract environment variables from various sources."""
        env_vars = []

        # Check .env files
        env_files = [".env", ".env.example", ".env.template"]
        for env_file in env_files:
            env_path = service_dir / env_file
            if env_path.exists():
                try:
                    content = env_path.read_text()
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env_vars.append(
                                {
                                    "name": key.strip(),
                                    "value": value.strip(),
                                    "source": env_file,
                                    "description": "",
                                }
                            )
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse env file", file=str(env_path), error=str(e)
                    )

        # Check main application file for environment variable usage
        main_file = self._find_main_file(service_dir)
        if main_file:
            main_path = service_dir / main_file
            try:
                content = main_path.read_text()

                # Find os.environ or process.env usage
                env_pattern = r'os\.environ\.get\(["\']([^"\']+)["\']'
                env_matches = re.findall(env_pattern, content)

                for env_name in env_matches:
                    if not any(var["name"] == env_name for var in env_vars):
                        env_vars.append(
                            {
                                "name": env_name,
                                "value": "",
                                "source": "code",
                                "description": f"Used in {main_file}",
                            }
                        )

            except Exception as e:
                self.logger.warning(
                    "Failed to extract env vars from code", error=str(e)
                )

        return env_vars

    def _analyze_dependencies(self, service_dir: Path) -> List[Dict[str, str]]:
        """Analyze service dependencies."""
        dependencies = []

        # Python dependencies
        requirements_file = service_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text()
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse package==version or package>=version
                        if "==" in line:
                            name, version = line.split("==", 1)
                        elif ">=" in line:
                            name, version = line.split(">=", 1)
                        else:
                            name, version = line, ""

                        dependencies.append(
                            {
                                "name": name.strip(),
                                "version": version.strip(),
                                "type": "python",
                            }
                        )
            except Exception as e:
                self.logger.warning("Failed to parse requirements.txt", error=str(e))

        # Node.js dependencies
        package_json = service_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r") as f:
                    package_data = json.load(f)

                for dep_type in ["dependencies", "devDependencies"]:
                    deps = package_data.get(dep_type, {})
                    for name, version in deps.items():
                        dependencies.append(
                            {
                                "name": name,
                                "version": version,
                                "type": f"node-{dep_type}",
                            }
                        )
            except Exception as e:
                self.logger.warning("Failed to parse package.json", error=str(e))

        return dependencies

    def _find_documentation_files(self, service_dir: Path) -> List[str]:
        """Find documentation files in service directory."""
        doc_files = []

        doc_patterns = ["README*", "*.md", "docs/*"]

        for pattern in doc_patterns:
            for doc_file in service_dir.glob(pattern):
                if doc_file.is_file():
                    doc_files.append(str(doc_file.relative_to(service_dir)))

        return sorted(doc_files)

    def _extract_version(self, service_dir: Path) -> str:
        """Extract service version from various sources."""
        # Try pyproject.toml
        pyproject_file = service_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                content = pyproject_file.read_text()
                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    return version_match.group(1)
            except Exception:
                pass

        # Try package.json
        package_json = service_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r") as f:
                    package_data = json.load(f)
                    return package_data.get("version", "1.0.0")
            except Exception:
                pass

        # Try Git tags
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=service_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return "1.0.0"

    def generate_service_documentation(self, service_info: Dict[str, Any]) -> str:
        """Generate markdown documentation for a service."""
        lines = [
            f"# {service_info['name'].title()} Service",
            "",
            f"**Type:** {service_info['type'].title()}  ",
            f"**Language:** {service_info['language'].title()}  ",
            f"**Framework:** {service_info['framework'].title()}  ",
            f"**Version:** {service_info['version']}  ",
            "",
            "## Overview",
            "",
            service_info["description"]
            or f"The {service_info['name']} service is part of the Alice v2 system.",
            "",
        ]

        # Architecture section
        if service_info.get("dockerfile"):
            lines.extend(
                [
                    "## Architecture",
                    "",
                    f"**Base Image:** `{service_info['dockerfile']['base_image']}`  ",
                ]
            )

            if service_info["dockerfile"]["exposed_ports"]:
                lines.append(
                    f"**Exposed Ports:** {', '.join(service_info['dockerfile']['exposed_ports'])}  "
                )

            lines.append("")

        # Configuration section
        if service_info["environment_variables"]:
            lines.extend(
                [
                    "## Configuration",
                    "",
                    "### Environment Variables",
                    "",
                    "| Variable | Description | Source |",
                    "|----------|-------------|--------|",
                ]
            )

            for env_var in service_info["environment_variables"]:
                description = (
                    env_var["description"]
                    or f"Configuration for {env_var['name'].lower()}"
                )
                lines.append(
                    f"| `{env_var['name']}` | {description} | {env_var['source']} |"
                )

            lines.extend(["", ""])

        if service_info["config_files"]:
            lines.extend(
                [
                    "### Configuration Files",
                    "",
                ]
            )

            for config_file in service_info["config_files"]:
                lines.append(f"- `{config_file}`")

            lines.extend(["", ""])

        # Dependencies section
        if service_info["dependencies"]:
            lines.extend(["## Dependencies", ""])

            # Group dependencies by type
            dep_types = {}
            for dep in service_info["dependencies"]:
                dep_type = dep["type"]
                if dep_type not in dep_types:
                    dep_types[dep_type] = []
                dep_types[dep_type].append(dep)

            for dep_type, deps in dep_types.items():
                lines.extend(
                    [
                        f"### {dep_type.title()} Dependencies",
                        "",
                        "| Package | Version |",
                        "|---------|---------|",
                    ]
                )

                for dep in deps:
                    version = dep["version"] or "latest"
                    lines.append(f"| `{dep['name']}` | {version} |")

                lines.extend(["", ""])

        # API section (if applicable)
        if service_info["type"] == "api":
            lines.extend(
                [
                    "## API Reference",
                    "",
                    f"See [{service_info['name']} API Documentation](../api/{service_info['name']}_api.md) for detailed API reference.",
                    "",
                ]
            )

        # Deployment section
        lines.extend(
            [
                "## Deployment",
                "",
                "### Docker",
                "",
                f"The {service_info['name']} service runs in a Docker container.",
                "",
            ]
        )

        if service_info.get("dockerfile"):
            lines.extend(
                [
                    "**Build:**",
                    "```bash",
                    f"docker build -t alice-{service_info['name']} .",
                    "```",
                    "",
                    "**Run:**",
                    "```bash",
                ]
            )

            run_cmd = f"docker run -d --name alice-{service_info['name']}"

            # Add port mappings
            if service_info["dockerfile"]["exposed_ports"]:
                for port in service_info["dockerfile"]["exposed_ports"]:
                    run_cmd += f" -p {port}:{port}"

            run_cmd += f" alice-{service_info['name']}"
            lines.append(run_cmd)
            lines.extend(["```", ""])

        # Add docker-compose section
        lines.extend(
            [
                "### Docker Compose",
                "",
                f"The service is included in the main `docker-compose.yml` as `alice-{service_info['name']}`.",
                "",
                "**Start with all services:**",
                "```bash",
                "docker compose up -d",
                "```",
                "",
                "**Start only this service:**",
                "```bash",
                f"docker compose up -d {service_info['name']}",
                "```",
                "",
            ]
        )

        # Health checks
        lines.extend(
            [
                "## Health Checks",
                "",
            ]
        )

        if service_info["type"] == "api":
            lines.extend(
                [
                    "**Health Endpoint:** `GET /health`",
                    "",
                    "**Check service health:**",
                    "```bash",
                    "curl http://localhost:PORT/health",
                    "```",
                    "",
                ]
            )
        else:
            lines.extend(
                ["Health checks are performed via Docker container status.", ""]
            )

        # Logs section
        lines.extend(
            [
                "## Logs",
                "",
                "**View logs:**",
                "```bash",
                f"docker compose logs -f {service_info['name']}",
                "```",
                "",
                "**View live logs:**",
                "```bash",
                f"docker compose logs -f --tail=100 {service_info['name']}",
                "```",
                "",
            ]
        )

        # Troubleshooting section
        lines.extend(
            [
                "## Troubleshooting",
                "",
                "### Common Issues",
                "",
                "**Service won't start:**",
                "1. Check Docker daemon is running",
                "2. Verify all environment variables are set",
                "3. Check port availability",
                "4. Review service logs for errors",
                "",
                "**Service is unhealthy:**",
                "1. Check service logs for errors",
                "2. Verify dependencies are running",
                "3. Check resource usage (CPU/Memory)",
                "4. Restart the service",
                "",
                "**Restart service:**",
                "```bash",
                f"docker compose restart {service_info['name']}",
                "```",
                "",
            ]
        )

        # Development section
        if service_info["main_file"]:
            lines.extend(
                [
                    "## Development",
                    "",
                    f"**Main file:** `{service_info['main_file']}`",
                    "",
                    "**Local development:**",
                    "```bash",
                    "# Install dependencies",
                ]
            )

            if service_info["language"] == "python":
                lines.extend(
                    [
                        "pip install -r requirements.txt",
                        "",
                        "# Run locally",
                        f"python {service_info['main_file']}",
                    ]
                )
            elif service_info["language"] == "javascript":
                lines.extend(
                    [
                        "npm install",
                        "",
                        "# Run locally",
                        "npm start",
                    ]
                )

            lines.extend(["```", ""])

        # Related documentation
        if service_info["documentation_files"]:
            lines.extend(["## Related Documentation", ""])

            for doc_file in service_info["documentation_files"]:
                doc_name = Path(doc_file).stem.replace("_", " ").title()
                lines.append(f"- [{doc_name}]({doc_file})")

            lines.extend(["", ""])

        lines.extend(
            [
                "---",
                "",
                f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Alice v2 Service Documentation Generator*",
            ]
        )

        return "\n".join(lines)

    def generate_all_documentation(self):
        """Generate documentation for all discovered services."""
        self.logger.info("Starting service documentation generation")

        # Discover services
        services = self.discover_services()

        if not services:
            self.logger.warning("No services discovered")
            return

        # Generate documentation for each service
        for service_info in services:
            self.logger.info(
                "Generating service documentation", service=service_info["name"]
            )

            try:
                # Generate markdown documentation
                markdown_docs = self.generate_service_documentation(service_info)
                markdown_file = self.docs_dir / f"{service_info['name']}.md"

                with open(markdown_file, "w") as f:
                    f.write(markdown_docs)

                self.logger.info(
                    "Generated service documentation",
                    service=service_info["name"],
                    dependencies=len(service_info["dependencies"]),
                    env_vars=len(service_info["environment_variables"]),
                )

            except Exception as e:
                self.logger.error(
                    "Failed to generate service documentation",
                    service=service_info["name"],
                    error=str(e),
                )

        # Generate services index
        self._generate_services_index(services)

        self.logger.info(
            "Service documentation generation completed", services=len(services)
        )

    def _generate_services_index(self, services: List[Dict[str, Any]]):
        """Generate an index file for all service documentation."""
        lines = [
            "# Alice v2 Services Documentation",
            "",
            "Complete documentation for all Alice v2 services and components.",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Services:** {len(services)}  ",
            "",
            "## Services Overview",
            "",
        ]

        # Group services by type
        services_by_type = {}
        for service in services:
            service_type = service["type"]
            if service_type not in services_by_type:
                services_by_type[service_type] = []
            services_by_type[service_type].append(service)

        # Generate documentation for each type
        for service_type, type_services in sorted(services_by_type.items()):
            lines.extend([f"### {service_type.title()} Services", ""])

            for service in type_services:
                lines.extend(
                    [
                        f"#### {service['name'].title()}",
                        "",
                        service["description"]
                        or f"{service['name']} service component",
                        "",
                        f"- **Language:** {service['language'].title()}",
                        f"- **Framework:** {service['framework'].title()}",
                        f"- **Version:** {service['version']}",
                        f"- **Documentation:** [{service['name']}.md]({service['name']}.md)",
                        "",
                    ]
                )

        # Add quick start section
        lines.extend(
            [
                "## Quick Start",
                "",
                "**Start all services:**",
                "```bash",
                "docker compose up -d",
                "```",
                "",
                "**Check service status:**",
                "```bash",
                "docker compose ps",
                "```",
                "",
                "**View all logs:**",
                "```bash",
                "docker compose logs -f",
                "```",
                "",
            ]
        )

        # Add architecture diagram reference
        lines.extend(
            [
                "## Architecture",
                "",
                "For a complete system architecture overview, see:",
                "- [System Blueprint](../ALICE_SYSTEM_BLUEPRINT.md)",
                "- [Architecture Documentation](../architecture/)",
                "",
                "## Service Dependencies",
                "",
                "The services have the following dependency relationships:",
                "",
            ]
        )

        # Simple dependency information
        api_services = [s for s in services if s["type"] == "api"]
        if api_services:
            lines.extend(["**API Services:**", ""])
            for service in api_services:
                lines.append(
                    f"- `{service['name']}` - {service['description'] or 'API service'}"
                )
            lines.append("")

        other_services = [s for s in services if s["type"] != "api"]
        if other_services:
            lines.extend(["**Support Services:**", ""])
            for service in other_services:
                lines.append(
                    f"- `{service['name']}` - {service['description'] or f'{service["type"]} service'}"
                )
            lines.append("")

        index_file = self.docs_dir / "README.md"
        with open(index_file, "w") as f:
            f.write("\n".join(lines))


def main():
    """Main entry point for the service documentation generator."""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        project_root = Path(__file__).parent.parent.parent

    generator = ServiceDocumentationGenerator(project_root)
    generator.generate_all_documentation()


if __name__ == "__main__":
    main()
