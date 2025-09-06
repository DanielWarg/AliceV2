#!/usr/bin/env python3
"""
Markdown Synchronization System for Alice v2
Automatically detects, analyzes and synchronizes all .md files to prevent documentation drift.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)


class MarkdownSyncSystem:
    """Comprehensive system for synchronizing all markdown documentation."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.excluded_dirs = {".venv", "node_modules", ".git", "__pycache__"}
        self.analysis_results = {}
        
    def find_all_markdown_files(self) -> List[Path]:
        """Find all markdown files in the project."""
        md_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(Path(root) / file)
                    
        return sorted(md_files)
    
    def analyze_file_content(self, file_path: Path) -> Dict:
        """Analyze markdown file content for metadata extraction."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            analysis = {
                'file_path': str(file_path),
                'relative_path': str(file_path.relative_to(self.project_root)),
                'size': len(content),
                'lines': len(content.split('\n')),
                'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'headers': self._extract_headers(content),
                'references': self._extract_references(content),
                'status_indicators': self._extract_status_indicators(content),
                'outdated_indicators': self._check_outdated_content(content),
                'duplicates': [],  # Will be filled by duplicate detection
                'category': self._categorize_file(file_path),
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {'error': str(e)}
    
    def _extract_headers(self, content: str) -> List[str]:
        """Extract all markdown headers."""
        headers = []
        for line in content.split('\n'):
            if line.strip().startswith('#'):
                headers.append(line.strip())
        return headers
    
    def _extract_references(self, content: str) -> List[str]:
        """Extract file references and links."""
        references = []
        
        # File references like README.md, docs/something.md
        file_refs = re.findall(r'[A-Z_]+\.md|docs/[^)\s]+\.md|\w+/[^)\s]+\.md', content)
        references.extend(file_refs)
        
        # Step references
        step_refs = re.findall(r'Step \d+\.?\d*', content, re.IGNORECASE)
        references.extend(step_refs)
        
        # Version/phase references  
        phase_refs = re.findall(r'Phase \d+|v\d+\.\d+|version \d+', content, re.IGNORECASE)
        references.extend(phase_refs)
        
        return list(set(references))
    
    def _extract_status_indicators(self, content: str) -> List[str]:
        """Extract status indicators like dates, versions, progress markers."""
        indicators = []
        
        # Dates
        dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', content)
        indicators.extend([f"date:{date}" for date in dates])
        
        # Progress indicators
        progress = re.findall(r'✅|❌|🚀|⚠️|🔄|IN PROGRESS|COMPLETE|TODO', content)
        indicators.extend([f"status:{p}" for p in progress])
        
        # Version indicators
        versions = re.findall(r'v\d+\.\d+\.\d+|version \d+\.\d+', content, re.IGNORECASE)
        indicators.extend([f"version:{v}" for v in versions])
        
        return indicators
    
    def _check_outdated_content(self, content: str) -> List[str]:
        """Check for potentially outdated content patterns."""
        outdated_patterns = [
            # Old step references that are likely outdated
            (r'Step [1-7]\.?\d*', 'old_step'),
            (r'Phase [1-2]', 'old_phase'), 
            (r'Current.*Step 8\.5', 'specific_old_step'),
            # Old tool/precision metrics that changed
            (r'tool precision.*54\.7%', 'old_metrics'),
            (r'Latency P95.*6897ms', 'old_latency'),
            # Old port references
            (r'localhost:1800[0-9]', 'old_port'),
            # Deprecated file references
            (r'auto_verify\.sh', 'deprecated_script'),
            # Old architectural references
            (r'Intent-Guard', 'old_component'),
        ]
        
        issues = []
        for pattern, issue_type in outdated_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(issue_type)
                
        return issues
    
    def _categorize_file(self, file_path: Path) -> str:
        """Categorize the markdown file based on its location and name."""
        relative_path = str(file_path.relative_to(self.project_root)).lower()
        
        if 'fibonacci' in relative_path:
            return 'fibonacci_docs'
        elif relative_path.startswith('docs/archive'):
            return 'archived'
        elif relative_path.startswith('runbooks/'):
            return 'runbooks'
        elif relative_path.startswith('.github/'):
            return 'github_templates'
        elif relative_path.startswith('.cursor/'):
            return 'cursor_config'
        elif relative_path in ['readme.md', 'agents.md', 'roadmap.md']:
            return 'core_docs'
        elif 'test' in relative_path:
            return 'test_docs'
        else:
            return 'general'
    
    def detect_duplicates(self, all_analyses: List[Dict]) -> Dict[str, List[str]]:
        """Detect potential duplicate content across files."""
        duplicates = {}
        
        # Group by similar headers
        header_groups = {}
        for analysis in all_analyses:
            if 'headers' in analysis and analysis['headers']:
                main_header = analysis['headers'][0] if analysis['headers'] else 'no_header'
                header_key = re.sub(r'[^a-zA-Z0-9]', '', main_header.lower())
                
                if header_key not in header_groups:
                    header_groups[header_key] = []
                header_groups[header_key].append(analysis['relative_path'])
        
        # Flag groups with multiple files
        for header_key, files in header_groups.items():
            if len(files) > 1 and header_key != 'noheader':
                duplicates[f"similar_headers_{header_key}"] = files
        
        # Check for similar file names
        name_groups = {}
        for analysis in all_analyses:
            file_name = Path(analysis['relative_path']).stem.lower()
            # Remove version numbers and dates for comparison
            clean_name = re.sub(r'[_\-v]\d+.*', '', file_name)
            
            if clean_name not in name_groups:
                name_groups[clean_name] = []
            name_groups[clean_name].append(analysis['relative_path'])
        
        for clean_name, files in name_groups.items():
            if len(files) > 1:
                duplicates[f"similar_names_{clean_name}"] = files
        
        return duplicates
    
    def generate_sync_recommendations(self, all_analyses: List[Dict]) -> Dict:
        """Generate recommendations for synchronizing documentation."""
        recommendations = {
            'critical_updates': [],
            'merge_candidates': [],
            'archive_candidates': [],
            'outdated_files': [],
            'sync_actions': []
        }
        
        for analysis in all_analyses:
            file_path = analysis['relative_path']
            
            # Critical updates needed
            if analysis.get('outdated_indicators'):
                recommendations['critical_updates'].append({
                    'file': file_path,
                    'issues': analysis['outdated_indicators'],
                    'priority': 'high' if 'cursorrules' in file_path else 'medium'
                })
            
            # Files that should be archived
            if analysis['category'] == 'archived' or 'archive' in file_path:
                recommendations['archive_candidates'].append(file_path)
            
            # Old test results or temporary files
            if ('test_results' in file_path or 
                'DAILY_STATUS' in file_path or
                analysis.get('size', 0) < 100):  # Very small files
                recommendations['archive_candidates'].append(file_path)
        
        # Detect merge candidates from duplicates
        duplicates = self.detect_duplicates(all_analyses)
        for group_name, files in duplicates.items():
            if 'similar' in group_name and len(files) > 1:
                recommendations['merge_candidates'].append({
                    'group': group_name,
                    'files': files,
                    'action': 'consider_merging'
                })
        
        return recommendations
    
    def create_master_sync_plan(self) -> Dict:
        """Create comprehensive synchronization plan."""
        logger.info("Starting comprehensive markdown synchronization analysis")
        
        # Find all files
        md_files = self.find_all_markdown_files()
        logger.info(f"Found {len(md_files)} markdown files")
        
        # Analyze each file
        all_analyses = []
        for file_path in md_files:
            analysis = self.analyze_file_content(file_path)
            if 'error' not in analysis:
                all_analyses.append(analysis)
        
        # Generate recommendations
        recommendations = self.generate_sync_recommendations(all_analyses)
        
        # Create sync plan
        sync_plan = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(md_files),
            'categories': {},
            'duplicates': self.detect_duplicates(all_analyses),
            'recommendations': recommendations,
            'priority_actions': self._create_priority_actions(recommendations),
            'auto_fixes': self._create_auto_fixes(all_analyses),
        }
        
        # Group by category
        for analysis in all_analyses:
            category = analysis.get('category', 'unknown')
            if category not in sync_plan['categories']:
                sync_plan['categories'][category] = []
            sync_plan['categories'][category].append(analysis['relative_path'])
        
        return sync_plan
    
    def _create_priority_actions(self, recommendations: Dict) -> List[Dict]:
        """Create prioritized list of actions."""
        actions = []
        
        # Critical updates first
        for update in recommendations['critical_updates']:
            if update['priority'] == 'high':
                actions.append({
                    'priority': 1,
                    'action': 'update_file',
                    'file': update['file'],
                    'reason': f"Critical outdated content: {', '.join(update['issues'])}"
                })
        
        # Archive old files
        for file_path in recommendations['archive_candidates'][:5]:  # Limit to top 5
            actions.append({
                'priority': 2,
                'action': 'archive_file',
                'file': file_path,
                'reason': "File appears outdated or redundant"
            })
        
        return sorted(actions, key=lambda x: x['priority'])
    
    def _create_auto_fixes(self, all_analyses: List[Dict]) -> Dict:
        """Create automated fixes that can be applied."""
        auto_fixes = {
            'cursorrules_update': self._generate_cursorrules_update(),
            'status_file_merge': self._plan_status_file_merge(),
            'fibonacci_docs_consolidation': self._plan_fibonacci_consolidation(),
        }
        
        return auto_fixes
    
    def _generate_cursorrules_update(self) -> Dict:
        """Generate updated .cursorrules content."""
        return {
            'action': 'replace_file',
            'target': '.cursorrules',
            'reason': 'File contains severely outdated information',
            'new_content': """# Alice v2 Cursor Rules
*Instructions for AI coding assistant working on Alice v2*

## 🚀 MANDATORY STARTUP SEQUENCE

**ALWAYS read these files FIRST when starting a new chat:**

1. **`AGENTS.md`** - AI agent orientation and current project context
2. **`README.md`** - Project overview and architecture 
3. **`ALICE_SYSTEM_BLUEPRINT.md`** - Detailed system architecture
4. **`ROADMAP.md`** - Current development milestones

## 📋 PROJECT CONTEXT

- **Current Phase**: Production Optimization Phase
- **Current Focus**: Fibonacci Mathematical Optimization (φ=1.618)
- **Language**: Swedish language optimization for Alice AI Assistant
- **Architecture**: Microservices with Docker orchestration

## 🛠️ DEVELOPMENT PRINCIPLES

- **Fibonacci Optimization**: All performance tuning uses Golden Ratio principles
- **Real Integration**: No mocks, test against real services with make up/down
- **Production Ready**: Everything deployment-ready from day 1
- **Observable**: Structured logging and real-time monitoring
- **Security First**: Guardian system provides brownout protection

## 🔧 WORKFLOW

1. **Start**: Read AGENTS.md for current context and priorities
2. **Understand**: Check ALICE_SYSTEM_BLUEPRINT.md for architecture
3. **Plan**: Use TodoWrite tool to track progress
4. **Implement**: Follow Fibonacci optimization principles
5. **Test**: Verify all services healthy with docker ps
6. **Monitor**: Check training progress and cache performance

## 🎯 CURRENT SYSTEM STATUS

- **Services**: orchestrator (8000), guardian (8787), nlu (9002), cache (6379)
- **Training**: Fibonacci cache optimization with φ=1.618
- **Documentation**: Auto-synced via pre-commit hooks and GitHub Actions
- **Cache Target**: 40%+ hit rate (from 10% baseline)

## 📊 KEY METRICS

- **Cache Hit Rate**: Monitor via scripts/fibonacci_simple_training.py
- **Response Time**: Target sub-200ms with Fibonacci scaling
- **System Health**: All services must show (healthy) in docker ps
- **Documentation**: All .md files auto-synced and validated

## 🚨 CRITICAL RULES

- **Never commit** without pre-commit hooks passing
- **Always use** TodoWrite for task tracking
- **Follow** Fibonacci principles in optimization
- **Keep** documentation synchronized
- **Test** with real services, not mocks

---

*Updated: {datetime.now().strftime('%Y-%m-%d')} | For: Alice v2 Production System*"""
        }
    
    def _plan_status_file_merge(self) -> Dict:
        """Plan merging of duplicate status files."""
        return {
            'action': 'merge_files',
            'targets': ['STATUS.md', 'PROJECT_STATUS.md'],
            'reason': 'Duplicate status tracking files should be consolidated',
            'strategy': 'merge_into_STATUS_md'
        }
    
    def _plan_fibonacci_consolidation(self) -> Dict:
        """Plan Fibonacci documentation consolidation."""
        return {
            'action': 'consolidate_directory',
            'target': 'docs/fibonacci/',
            'reason': 'Multiple overlapping Fibonacci guides need consolidation',
            'strategy': 'keep_FIBONACCI_MASTER_GUIDE_as_primary'
        }
    
    def save_sync_plan(self, sync_plan: Dict, output_path: str = None) -> str:
        """Save synchronization plan to file."""
        if output_path is None:
            output_path = self.project_root / 'docs' / 'markdown_sync_plan.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sync_plan, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sync plan saved to {output_path}")
        return str(output_path)


def main():
    """Main execution function."""
    project_root = Path(__file__).parent.parent.parent
    sync_system = MarkdownSyncSystem(str(project_root))
    
    print("🔍 Analyzing all markdown files for synchronization...")
    sync_plan = sync_system.create_master_sync_plan()
    
    # Save plan
    plan_path = sync_system.save_sync_plan(sync_plan)
    
    # Print summary
    print(f"\n📊 MARKDOWN SYNC ANALYSIS COMPLETE")
    print(f"Total files analyzed: {sync_plan['total_files']}")
    print(f"Critical updates needed: {len(sync_plan['recommendations']['critical_updates'])}")
    print(f"Archive candidates: {len(sync_plan['recommendations']['archive_candidates'])}")
    print(f"Duplicate groups: {len(sync_plan['duplicates'])}")
    print(f"Priority actions: {len(sync_plan['priority_actions'])}")
    print(f"\n📋 Full analysis saved to: {plan_path}")
    
    # Print top priority actions
    print(f"\n🚨 TOP PRIORITY ACTIONS:")
    for action in sync_plan['priority_actions'][:5]:
        print(f"  {action['priority']}. {action['action']}: {action['file']}")
        print(f"     Reason: {action['reason']}")
    
    return sync_plan


if __name__ == "__main__":
    sync_plan = main()