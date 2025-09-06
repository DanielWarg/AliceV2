#!/usr/bin/env python3
"""
MkDocs Configuration Generator for Alice v2

Automatically generates MkDocs configuration based on the current documentation
structure, discovered services, and project configuration. Creates a complete
mkdocs.yml with proper navigation, plugins, and theme settings.

Features:
- Dynamic navigation generation from documentation structure
- Service-aware API documentation organization
- Plugin configuration based on available content
- Theme customization for Alice v2 branding
- Integration with existing documentation automation
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import structlog
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class MkDocsConfigGenerator:
    """Generates MkDocs configuration for Alice v2 documentation."""

    def __init__(self, project_root: Path):
        """Initialize the MkDocs config generator."""
        self.project_root = Path(project_root)
        self.docs_dir = self.project_root / "docs"
        self.config_path = self.project_root / "mkdocs.yml"
        self.logger = structlog.get_logger(__name__)

        # Load project configuration
        self.project_config = self._load_project_config()

    def _load_project_config(self) -> Dict[str, Any]:
        """Load project configuration from various sources."""
        config = {
            "site_name": "Alice v2 AI Assistant",
            "site_description": "Comprehensive documentation for Alice v2 AI Assistant",
            "site_url": "https://alice-v2.github.io/",
            "repo_url": "https://github.com/alice-v2/alice-v2",
            "repo_name": "alice-v2/alice-v2",
        }

        # Try to load from docs automation config
        automation_config_path = self.project_root / ".docs-automation.yml"
        if automation_config_path.exists():
            try:
                with open(automation_config_path, "r") as f:
                    automation_config = yaml.safe_load(f)

                config["site_name"] = automation_config.get(
                    "project_name", config["site_name"]
                )

                # Update URLs if specified
                tools_config = automation_config.get("tools", {})
                mkdocs_config = tools_config.get("mkdocs", {})
                if "site_url" in mkdocs_config:
                    config["site_url"] = mkdocs_config["site_url"]

            except Exception as e:
                self.logger.warning("Failed to load automation config", error=str(e))

        return config

    def discover_documentation_structure(self) -> Dict[str, List[str]]:
        """Discover the current documentation structure."""
        structure = {
            "root": [],
            "api": [],
            "services": [],
            "architecture": [],
            "guides": [],
            "deployment": [],
            "troubleshooting": [],
            "performance": [],
            "security": [],
            "contributing": [],
        }

        # Scan root level markdown files
        for md_file in self.project_root.glob("*.md"):
            if md_file.name != "README.md":  # README will be index
                structure["root"].append(md_file.name)

        # Scan documentation directories
        if self.docs_dir.exists():
            for category in structure.keys():
                if category == "root":
                    continue

                category_dir = self.docs_dir / category
                if category_dir.exists():
                    # Get all markdown files in this category
                    for md_file in category_dir.glob("**/*.md"):
                        rel_path = str(md_file.relative_to(self.docs_dir))
                        structure[category].append(rel_path)

        # Sort all lists for consistent ordering
        for category in structure:
            structure[category].sort()

        return structure

    def generate_navigation(
        self, structure: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Generate navigation structure for MkDocs."""
        nav = []

        # Home page
        nav.append({"Home": "index.md"})

        # Quick Start section
        if "ROADMAP.md" in structure["root"] or "CONTRIBUTING.md" in structure["root"]:
            quick_start = {}
            if "ROADMAP.md" in structure["root"]:
                quick_start["Roadmap"] = "ROADMAP.md"
            if "CONTRIBUTING.md" in structure["root"]:
                quick_start["Contributing"] = "CONTRIBUTING.md"
            nav.append({"Quick Start": quick_start})

        # API Documentation
        if structure["api"]:
            api_nav = {}

            # Add API index if it exists
            if "api/README.md" in structure["api"]:
                api_nav["Overview"] = "api/README.md"

            # Group by service
            services = {}
            other_api_docs = []

            for api_file in structure["api"]:
                if api_file == "api/README.md":
                    continue

                # Check if it's a service API doc (service_name_api.md)
                filename = Path(api_file).name
                if filename.endswith("_api.md"):
                    service_name = filename.replace("_api.md", "")
                    service_title = service_name.replace("_", " ").title()
                    services[service_title] = api_file
                elif filename.endswith("_openapi.json"):
                    # Skip OpenAPI specs in navigation
                    continue
                else:
                    other_api_docs.append(api_file)

            # Add services to navigation
            if services:
                for service_title, service_file in sorted(services.items()):
                    api_nav[f"{service_title} API"] = service_file

            # Add other API docs
            for doc in other_api_docs:
                title = Path(doc).stem.replace("_", " ").title()
                api_nav[title] = doc

            if api_nav:
                nav.append({"API Reference": api_nav})

        # Services Documentation
        if structure["services"]:
            services_nav = {}

            for service_file in structure["services"]:
                title = Path(service_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                services_nav[title] = service_file

            nav.append({"Services": services_nav})

        # Architecture Documentation
        if structure["architecture"]:
            arch_nav = {}

            # Prioritize certain architecture docs
            priority_docs = {
                "ALICE_SYSTEM_BLUEPRINT.md": "System Blueprint",
                "architecture/system_overview.md": "System Overview",
                "architecture/service_architecture.md": "Service Architecture",
                "architecture/data_flow.md": "Data Flow",
            }

            # Add priority docs first
            for arch_file in structure["architecture"]:
                if arch_file in priority_docs:
                    arch_nav[priority_docs[arch_file]] = arch_file

            # Add remaining docs
            for arch_file in structure["architecture"]:
                if arch_file not in priority_docs:
                    title = Path(arch_file).stem.replace("_", " ").title()
                    if title == "README":
                        title = "Overview"
                    arch_nav[title] = arch_file

            # Add root level architecture docs
            for doc in structure["root"]:
                if "BLUEPRINT" in doc or "ARCHITECTURE" in doc:
                    title = Path(doc).stem.replace("_", " ").title()
                    arch_nav[title] = doc

            if arch_nav:
                nav.append({"Architecture": arch_nav})

        # User Guides
        if structure["guides"]:
            guides_nav = {}

            # Prioritize setup and getting started guides
            priority_guides = {
                "guides/quick_start.md": "Quick Start",
                "guides/installation.md": "Installation",
                "guides/configuration.md": "Configuration",
                "guides/deployment.md": "Deployment",
            }

            for guide_file in structure["guides"]:
                if guide_file in priority_guides:
                    guides_nav[priority_guides[guide_file]] = guide_file

            for guide_file in structure["guides"]:
                if guide_file not in priority_guides:
                    title = Path(guide_file).stem.replace("_", " ").title()
                    if title == "README":
                        title = "Overview"
                    guides_nav[title] = guide_file

            if guides_nav:
                nav.append({"User Guides": guides_nav})

        # Deployment
        if structure["deployment"]:
            deploy_nav = {}
            for deploy_file in structure["deployment"]:
                title = Path(deploy_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                deploy_nav[title] = deploy_file
            nav.append({"Deployment": deploy_nav})

        # Performance & Monitoring
        if structure["performance"]:
            perf_nav = {}
            for perf_file in structure["performance"]:
                title = Path(perf_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                perf_nav[title] = perf_file
            nav.append({"Performance": perf_nav})

        # Security
        if structure["security"]:
            security_nav = {}
            for security_file in structure["security"]:
                title = Path(security_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                security_nav[title] = security_file
            nav.append({"Security": security_nav})

        # Add root level important docs
        important_root_docs = {
            "TESTING_STRATEGY.md": "Testing Strategy",
            "SECURITY_AND_PRIVACY.md": "Security & Privacy",
            "STATUS.md": "System Status",
        }

        reference_nav = {}
        for doc_file, title in important_root_docs.items():
            if doc_file in structure["root"]:
                reference_nav[title] = doc_file

        if reference_nav:
            nav.append({"Reference": reference_nav})

        # Troubleshooting
        if structure["troubleshooting"]:
            troubleshooting_nav = {}
            for trouble_file in structure["troubleshooting"]:
                title = Path(trouble_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                troubleshooting_nav[title] = trouble_file
            nav.append({"Troubleshooting": troubleshooting_nav})

        # Contributing
        if structure["contributing"]:
            contrib_nav = {}
            for contrib_file in structure["contributing"]:
                title = Path(contrib_file).stem.replace("_", " ").title()
                if title == "README":
                    title = "Overview"
                contrib_nav[title] = contrib_file
            nav.append({"Contributing": contrib_nav})

        return nav

    def detect_required_plugins(self, structure: Dict[str, List[str]]) -> List[str]:
        """Detect which MkDocs plugins are needed based on content."""
        plugins = ["search"]  # Always include search

        # Check for content that requires specific plugins
        all_files = []
        for file_list in structure.values():
            all_files.extend(file_list)

        # Check for Mermaid diagrams
        has_mermaid = False
        for file_path in all_files:
            full_path = (
                self.docs_dir / file_path
                if not Path(file_path).is_absolute()
                else Path(file_path)
            )
            if full_path.exists():
                try:
                    content = full_path.read_text()
                    if "```mermaid" in content or "mermaid" in content.lower():
                        has_mermaid = True
                        break
                except Exception:
                    continue

        if has_mermaid:
            plugins.append("mermaid2")

        # Check for OpenAPI specs
        has_openapi = any("openapi.json" in f for f in all_files)
        if has_openapi:
            plugins.append("swagger-ui-tag")

        # Check for generated content
        if structure["api"] or structure["services"]:
            plugins.extend(["gen-files", "literate-nav"])

        # Remove duplicates while preserving order
        seen = set()
        unique_plugins = []
        for plugin in plugins:
            if plugin not in seen:
                seen.add(plugin)
                unique_plugins.append(plugin)

        return unique_plugins

    def generate_theme_config(self) -> Dict[str, Any]:
        """Generate theme configuration for Alice v2."""
        return {
            "name": "material",
            "palette": [
                {
                    "scheme": "default",
                    "primary": "blue",
                    "accent": "light-blue",
                    "toggle": {
                        "icon": "material/brightness-7",
                        "name": "Switch to dark mode",
                    },
                },
                {
                    "scheme": "slate",
                    "primary": "blue",
                    "accent": "light-blue",
                    "toggle": {
                        "icon": "material/brightness-4",
                        "name": "Switch to light mode",
                    },
                },
            ],
            "features": [
                "navigation.tabs",
                "navigation.sections",
                "navigation.expand",
                "navigation.top",
                "navigation.tracking",
                "search.highlight",
                "search.share",
                "search.suggest",
                "header.autohide",
                "content.code.copy",
                "content.code.annotate",
            ],
            "icon": {"repo": "fontawesome/brands/github", "logo": "material/robot"},
            "font": {"text": "Inter", "code": "JetBrains Mono"},
            "custom_dir": "docs/overrides",
        }

    def generate_markdown_extensions(self, plugins: List[str]) -> List[Any]:
        """Generate markdown extensions configuration."""
        extensions = [
            "toc",
            "admonition",
            "attr_list",
            "md_in_html",
            "def_list",
            "footnotes",
            "meta",
            {"codehilite": {"use_pygments": True, "guess_lang": False}},
            {"pymdownx.superfences": {"custom_fences": []}},
            "pymdownx.tabbed",
            "pymdownx.details",
            "pymdownx.critic",
            "pymdownx.caret",
            "pymdownx.mark",
            "pymdownx.tilde",
            "pymdownx.keys",
            "pymdownx.snippets",
            {
                "pymdownx.highlight": {
                    "anchor_linenums": True,
                    "line_spans": "__span",
                    "pygments_lang_class": True,
                }
            },
            {"pymdownx.inlinehilite": {"style_plain_text": True}},
            "pymdownx.tasklist",
            {
                "pymdownx.emoji": {
                    "emoji_index": "!!python/name:materialx.emoji.twemoji",
                    "emoji_generator": "!!python/name:materialx.emoji.to_svg",
                }
            },
        ]

        # Add Mermaid support if needed
        if "mermaid2" in plugins:
            extensions[7]["pymdownx.superfences"]["custom_fences"].append(
                {
                    "name": "mermaid",
                    "class": "mermaid",
                    "format": "!!python/name:pymdownx.superfences.fence_code_format",
                }
            )

        return extensions

    def generate_full_config(self) -> Dict[str, Any]:
        """Generate complete MkDocs configuration."""
        structure = self.discover_documentation_structure()
        navigation = self.generate_navigation(structure)
        plugins = self.detect_required_plugins(structure)
        theme = self.generate_theme_config()
        extensions = self.generate_markdown_extensions(plugins)

        config = {
            "site_name": self.project_config["site_name"],
            "site_description": self.project_config["site_description"],
            "site_url": self.project_config["site_url"],
            "repo_url": self.project_config["repo_url"],
            "repo_name": self.project_config["repo_name"],
            "docs_dir": "docs",
            "site_dir": "site",
            "theme": theme,
            "plugins": plugins,
            "nav": navigation,
            "markdown_extensions": extensions,
            "extra": {
                "generator": False,  # Don't show "Made with MkDocs"
                "version": {"provider": "mike"},
                "social": [
                    {
                        "icon": "fontawesome/brands/github",
                        "link": self.project_config["repo_url"],
                    }
                ],
                "analytics": {
                    "feedback": {
                        "title": "Was this page helpful?",
                        "ratings": [
                            {
                                "icon": "material/emoticon-happy-outline",
                                "name": "This page was helpful",
                                "data": 1,
                                "note": "Thanks for your feedback!",
                            },
                            {
                                "icon": "material/emoticon-sad-outline",
                                "name": "This page could be improved",
                                "data": 0,
                                "note": "Thanks for your feedback! Help us improve this page by <a href='https://github.com/alice-v2/alice-v2/issues/new/?title=[Docs] Feedback' target='_blank' rel='noopener'>opening an issue</a>.",
                            },
                        ],
                    }
                },
            },
            "extra_css": ["stylesheets/extra.css"],
            "extra_javascript": ["javascripts/extra.js"],
            "copyright": f"Copyright &copy; {datetime.now().year} Alice v2 Team",
            "watch": ["docs", "mkdocs.yml"],
        }

        # Add plugin configurations
        plugin_configs = {}

        if "mermaid2" in plugins:
            plugin_configs["mermaid2"] = {"version": "10.6.1"}

        if "swagger-ui-tag" in plugins:
            plugin_configs["swagger-ui-tag"] = {
                "background": "White",
                "docExpansion": "none",
            }

        if "gen-files" in plugins:
            plugin_configs["gen-files"] = {
                "scripts": ["scripts/auto_docs/gen_ref_nav.py"]
            }

        # Convert plugin list to plugin configs if needed
        if plugin_configs:
            new_plugins = []
            for plugin in plugins:
                if plugin in plugin_configs:
                    new_plugins.append({plugin: plugin_configs[plugin]})
                else:
                    new_plugins.append(plugin)
            config["plugins"] = new_plugins

        return config

    def write_config(self, config: Dict[str, Any]) -> bool:
        """Write MkDocs configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(
                    config, f, default_flow_style=False, sort_keys=False, indent=2
                )

            self.logger.info("MkDocs configuration written", path=str(self.config_path))
            return True

        except Exception as e:
            self.logger.error("Failed to write MkDocs configuration", error=str(e))
            return False

    def create_supporting_files(self):
        """Create supporting files for MkDocs."""
        # Create index.md if it doesn't exist
        index_file = self.docs_dir / "index.md"
        if not index_file.exists():
            readme_file = self.project_root / "README.md"
            if readme_file.exists():
                # Copy README to index
                try:
                    import shutil

                    shutil.copy2(readme_file, index_file)
                    self.logger.info("Created index.md from README.md")
                except Exception as e:
                    self.logger.warning("Failed to copy README to index", error=str(e))
            else:
                # Create basic index
                index_content = f"""# {self.project_config['site_name']}

{self.project_config['site_description']}

## Welcome

This is the comprehensive documentation for Alice v2 AI Assistant.

## Getting Started

- [Quick Start](guides/quick_start.md)
- [Installation](guides/installation.md)
- [API Reference](api/)

## Architecture

- [System Blueprint](ALICE_SYSTEM_BLUEPRINT.md)
- [Services](services/)

## Contributing

- [Contributing Guide](CONTRIBUTING.md)
- [Development Workflow](guides/development.md)

---

*Documentation generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
                index_file.write_text(index_content)
                self.logger.info("Created basic index.md")

        # Create extra CSS file
        css_dir = self.docs_dir / "stylesheets"
        css_dir.mkdir(exist_ok=True)

        extra_css = css_dir / "extra.css"
        if not extra_css.exists():
            css_content = """/* Alice v2 Documentation Custom Styles */

:root {
    --md-primary-fg-color: #2196F3;
    --md-accent-fg-color: #03A9F4;
}

/* Code blocks */
.highlight pre {
    border-radius: 6px;
}

/* Admonitions */
.md-typeset .admonition {
    border-radius: 6px;
}

/* Navigation */
.md-nav__title {
    font-weight: 600;
}

/* Tables */
.md-typeset table:not([class]) {
    border-radius: 6px;
    overflow: hidden;
}

/* Custom Alice v2 branding */
.alice-logo {
    height: 2rem;
    vertical-align: middle;
}

.performance-metric {
    background: var(--md-code-bg-color);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: var(--md-code-font-family);
}

/* API documentation styling */
.api-endpoint {
    background: var(--md-code-bg-color);
    padding: 1em;
    border-radius: 6px;
    margin: 1em 0;
}

.http-method {
    display: inline-block;
    padding: 0.2em 0.6em;
    border-radius: 3px;
    color: white;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 0.8em;
}

.http-method.get { background-color: #28a745; }
.http-method.post { background-color: #007bff; }
.http-method.put { background-color: #ffc107; color: #000; }
.http-method.delete { background-color: #dc3545; }
.http-method.patch { background-color: #6f42c1; }
"""
            extra_css.write_text(css_content)
            self.logger.info("Created extra.css")

        # Create extra JavaScript file
        js_dir = self.docs_dir / "javascripts"
        js_dir.mkdir(exist_ok=True)

        extra_js = js_dir / "extra.js"
        if not extra_js.exists():
            js_content = """// Alice v2 Documentation Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Add copy button functionality to code blocks
    const codeBlocks = document.querySelectorAll('.highlight');
    codeBlocks.forEach(block => {
        const button = document.createElement('button');
        button.className = 'copy-btn';
        button.textContent = 'Copy';
        button.onclick = () => {
            const code = block.querySelector('code').textContent;
            navigator.clipboard.writeText(code).then(() => {
                button.textContent = 'Copied!';
                setTimeout(() => button.textContent = 'Copy', 2000);
            });
        };
        block.appendChild(button);
    });
    
    // Add API endpoint styling
    const apiEndpoints = document.querySelectorAll('h4');
    apiEndpoints.forEach(heading => {
        const text = heading.textContent;
        const methodMatch = text.match(/^(GET|POST|PUT|DELETE|PATCH)\s+(.+)/i);
        if (methodMatch) {
            const method = methodMatch[1].toUpperCase();
            const path = methodMatch[2];
            
            heading.innerHTML = `
                <span class="http-method ${method.toLowerCase()}">${method}</span>
                <code>${path}</code>
            `;
        }
    });
});
"""
            extra_js.write_text(js_content)
            self.logger.info("Created extra.js")

        # Create overrides directory for theme customization
        overrides_dir = self.docs_dir / "overrides"
        overrides_dir.mkdir(exist_ok=True)

        # Create custom main template
        main_template = overrides_dir / "main.html"
        if not main_template.exists():
            template_content = """{% extends "base.html" %}

{% block announce %}
  <div class="md-banner md-banner--alice">
    <div class="md-banner__inner md-grid md-typeset">
      <p>
        🤖 <strong>Alice v2 AI Assistant</strong> - 
        Advanced AI assistant with Guardian safety system and real-time observability
      </p>
    </div>
  </div>
{% endblock %}

{% block footer %}
  {{ super() }}
  <div class="alice-footer">
    <div class="md-grid md-typeset">
      <div class="alice-footer__inner">
        <p>Built with ❤️ by the Alice v2 Team</p>
        <p>
          <a href="{{ config.repo_url }}">View on GitHub</a> •
          <a href="{{ config.repo_url }}/issues">Report Issue</a> •
          <a href="{{ config.repo_url }}/discussions">Discussions</a>
        </p>
      </div>
    </div>
  </div>
{% endblock %}
"""
            main_template.write_text(template_content)
            self.logger.info("Created main.html template")

    def generate(self) -> bool:
        """Generate complete MkDocs configuration and supporting files."""
        self.logger.info("Generating MkDocs configuration")

        try:
            # Ensure docs directory exists
            self.docs_dir.mkdir(exist_ok=True)

            # Generate configuration
            config = self.generate_full_config()

            # Write configuration
            success = self.write_config(config)

            if success:
                # Create supporting files
                self.create_supporting_files()

                self.logger.info(
                    "MkDocs configuration generated successfully",
                    nav_items=len(config["nav"]),
                    plugins=len(config["plugins"]),
                )

            return success

        except Exception as e:
            self.logger.error("Failed to generate MkDocs configuration", error=str(e))
            return False


def main():
    """Main entry point for MkDocs config generator."""
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        project_root = Path(__file__).parent.parent.parent

    generator = MkDocsConfigGenerator(project_root)
    success = generator.generate()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
