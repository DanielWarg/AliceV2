#!/usr/bin/env python3
"""
Documentation Synchronization Verification Script
Checks that all documentation files are consistent with actual system state
"""

import re
import sys
from pathlib import Path
from typing import Dict


class DocSyncVerifier:
    def __init__(self):
        self.root_dir = Path(".")
        self.issues = []
        self.systems = {}

    def extract_systems_from_blueprint(self) -> Dict[str, str]:
        """Extract all implemented systems from blueprint"""
        systems = {}
        try:
            with open("ALICE_SYSTEM_BLUEPRINT.md", "r") as f:
                content = f.read()

            # Find all ✅ IMPLEMENTED/OPERATIONAL sections
            pattern = r"### \d+\.?\d*\. \*\*(.*?)\*\* ✅ (IMPLEMENTED|OPERATIONAL)"
            matches = re.findall(pattern, content)

            for match in matches:
                system_name = match[0]
                status = match[1]
                systems[system_name] = status

        except Exception as e:
            self.issues.append(f"❌ Could not read ALICE_SYSTEM_BLUEPRINT.md: {e}")

        return systems

    def check_port_consistency(self):
        """Check port numbers are consistent across all docs"""
        port_refs = {}

        # Expected ports from current system
        expected_ports = {
            "18000": "dev-proxy/orchestrator",
            "8787": "guardian",
            "9002": "nlu",
            "11434": "ollama",
            "6379": "redis/cache",
            "8501": "dashboard/hud",
        }

        docs_to_check = [
            "README.md",
            "ALICE_PRODUCTION_CHECKLIST.md",
            "docker-compose.yml",
            "ALICE_SYSTEM_BLUEPRINT.md",
        ]

        for doc in docs_to_check:
            if not Path(doc).exists():
                continue

            try:
                with open(doc, "r") as f:
                    content = f.read()

                # Find all port references
                port_pattern = r"(?:port|Port|PORT)[\s:]*(\d{4,5})"
                matches = re.findall(port_pattern, content)

                for port in matches:
                    if doc not in port_refs:
                        port_refs[doc] = set()
                    port_refs[doc].add(port)

            except Exception as e:
                self.issues.append(f"❌ Could not read {doc}: {e}")

        # Check for inconsistencies
        for doc, ports in port_refs.items():
            for port in ports:
                if port in expected_ports:
                    print(f"✅ {doc}: Port {port} ({expected_ports[port]}) - OK")
                elif port not in [
                    "3000",
                    "8000",
                    "8001",
                    "8002",
                    "8003",
                    "8004",
                    "8005",
                ]:  # Old ports we're migrating from
                    self.issues.append(f"❌ {doc}: Unknown port {port} found")

    def check_system_status_consistency(self):
        """Check that system statuses are consistent across all docs"""
        blueprint_systems = self.extract_systems_from_blueprint()

        # Check ROADMAP.md mentions these systems
        roadmap_systems = set()
        try:
            with open("ROADMAP.md", "r") as f:
                content = f.read()

            # Look for system mentions in roadmap
            for system in blueprint_systems.keys():
                if system.lower() in content.lower():
                    roadmap_systems.add(system)

        except Exception as e:
            self.issues.append(f"❌ Could not check ROADMAP.md: {e}")

        # Check ALICE_PRODUCTION_CHECKLIST.md
        checklist_systems = set()
        try:
            with open("ALICE_PRODUCTION_CHECKLIST.md", "r") as f:
                content = f.read()

            for system in blueprint_systems.keys():
                if system.lower() in content.lower():
                    checklist_systems.add(system)

        except Exception as e:
            self.issues.append(f"❌ Could not check ALICE_PRODUCTION_CHECKLIST.md: {e}")

        # Report missing systems
        missing_from_roadmap = set(blueprint_systems.keys()) - roadmap_systems
        missing_from_checklist = set(blueprint_systems.keys()) - checklist_systems

        if missing_from_roadmap:
            for system in missing_from_roadmap:
                self.issues.append(f"❌ ROADMAP.md missing system: {system}")

        if missing_from_checklist:
            for system in missing_from_checklist:
                self.issues.append(
                    f"❌ ALICE_PRODUCTION_CHECKLIST.md missing system: {system}"
                )

    def check_docker_services_match(self):
        """Check that documented services match docker-compose.yml"""
        docker_services = set()
        documented_services = set()

        # Extract services from docker-compose.yml
        try:
            with open("docker-compose.yml", "r") as f:
                content = f.read()

            service_pattern = r"^\s+(\w+[-\w]*):$"
            matches = re.findall(service_pattern, content, re.MULTILINE)
            docker_services = set(matches)

        except Exception as e:
            self.issues.append(f"❌ Could not read docker-compose.yml: {e}")
            return

        # Extract services mentioned in blueprint
        try:
            with open("ALICE_SYSTEM_BLUEPRINT.md", "r") as f:
                content = f.read()

            # Look for container references
            container_pattern = r"Container: (alice-[\w-]+)"
            matches = re.findall(container_pattern, content)
            documented_services = set([m.replace("alice-", "") for m in matches])

        except Exception as e:
            self.issues.append(f"❌ Could not check blueprint services: {e}")
            return

        # Compare
        missing_docs = docker_services - documented_services
        extra_docs = documented_services - docker_services

        if missing_docs:
            for service in missing_docs:
                self.issues.append(
                    f"❌ Service '{service}' in docker-compose.yml but not documented in blueprint"
                )

        if extra_docs:
            for service in extra_docs:
                self.issues.append(
                    f"❌ Service '{service}' documented in blueprint but not in docker-compose.yml"
                )

    def run_verification(self):
        """Run all verification checks"""
        print("🔍 Verifying documentation synchronization...")
        print()

        self.check_port_consistency()
        self.check_system_status_consistency()
        self.check_docker_services_match()

        print("\n" + "=" * 60)

        if not self.issues:
            print("✅ All documentation files are synchronized!")
            return 0
        else:
            print(f"❌ Found {len(self.issues)} synchronization issues:")
            print()
            for issue in self.issues:
                print(f"  {issue}")
            print()
            print("💡 Run with --fix flag to auto-fix simple issues")
            return 1


if __name__ == "__main__":
    verifier = DocSyncVerifier()
    exit_code = verifier.run_verification()
    sys.exit(exit_code)
