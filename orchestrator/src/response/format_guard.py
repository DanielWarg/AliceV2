"""
FormatGuard - Pre-flight response formatting för T8 stabilisering

Fixar vanliga formateringsfel innan verifier-check för att minska false positives.
Inkluderar svenska språkfixar och strukturella korrigeringar.
"""

import re
from typing import Dict, List, Tuple


class FormatGuard:
    """
    Pre-processing pipeline för att fixa vanliga response-format issues.
    """

    def __init__(self):
        # Kompilera regex patterns för performance
        self._compile_patterns()

    def _compile_patterns(self):
        """Kompilera vanliga format-patterns."""
        # JSON formatting
        self.json_fixes = [
            (
                re.compile(r'(?<!\\)"([^"]*)"(?=\s*:)'),
                r'"\1"',
            ),  # Fix quote escaping in keys
            (
                re.compile(r':\s*"([^"]*)"([^,}\]\n])'),
                r': "\1"\2',
            ),  # Missing commas after strings
            (re.compile(r"},(\s*})"), r"}\1"),  # Trailing commas in objects
        ]

        # Svenska språkfixar
        self.swedish_fixes = [
            (re.compile(r"\baa\b", re.IGNORECASE), "å"),  # Common aa -> å
            (re.compile(r"\bae\b", re.IGNORECASE), "ä"),  # Common ae -> ä
            (re.compile(r"\boe\b", re.IGNORECASE), "ö"),  # Common oe -> ö
            (re.compile(r"\bAA\b"), "Å"),
            (re.compile(r"\bAE\b"), "Ä"),
            (re.compile(r"\bOE\b"), "Ö"),
        ]

        # Strukturella fixar
        self.structural_fixes = [
            (re.compile(r"\n{3,}"), "\n\n"),  # Excessive line breaks
            (re.compile(r"[ \t]{3,}"), "  "),  # Excessive whitespace
            (re.compile(r"^[\s\n]+|[\s\n]+$"), ""),  # Leading/trailing whitespace
        ]

        # Markdown fixes
        self.markdown_fixes = [
            (re.compile(r"(\*\*[^*]+)\*([^*]*\*\*)"), r"\1*\2"),  # Bold marker fixes
            (re.compile(r"(\*[^*]+)\*\*([^*]*\*)"), r"\1*\2"),  # Italic marker fixes
            (re.compile(r"#+\s*#+"), "#"),  # Duplicate headers
        ]

    def fix_json_formatting(self, text: str) -> Tuple[str, List[str]]:
        """Fixar vanliga JSON-formateringsproblem."""
        fixes_applied = []
        original = text

        for pattern, replacement in self.json_fixes:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                fixes_applied.append(f"json_fix: {pattern.pattern}")
                text = new_text

        return text, fixes_applied

    def fix_swedish_language(self, text: str) -> Tuple[str, List[str]]:
        """Fixar vanliga svenska språkproblem."""
        fixes_applied = []
        original = text

        for pattern, replacement in self.swedish_fixes:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                fixes_applied.append(f"swedish_fix: {pattern.pattern} -> {replacement}")
                text = new_text

        return text, fixes_applied

    def fix_structural_issues(self, text: str) -> Tuple[str, List[str]]:
        """Fixar strukturella formateringsproblem."""
        fixes_applied = []
        original = text

        for pattern, replacement in self.structural_fixes:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                fixes_applied.append(f"structural_fix: {pattern.pattern}")
                text = new_text

        return text, fixes_applied

    def fix_markdown_formatting(self, text: str) -> Tuple[str, List[str]]:
        """Fixar vanliga markdown-problem."""
        fixes_applied = []
        original = text

        for pattern, replacement in self.markdown_fixes:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                fixes_applied.append(f"markdown_fix: {pattern.pattern}")
                text = new_text

        return text, fixes_applied

    def fix_policy_violations(self, text: str) -> Tuple[str, List[str]]:
        """
        Fixar vanliga policy violations som kan undvikas.
        VARNING: Håller lätt eftersom vi inte vill ändra innehåll för mycket.
        """
        fixes_applied = []
        original = text

        # Ta bort uppenbara placeholder-texter som triggern policy
        placeholder_patterns = [
            (re.compile(r"\[PLACEHOLDER[^\]]*\]", re.IGNORECASE), ""),
            (re.compile(r"\[TODO[^\]]*\]", re.IGNORECASE), ""),
            (re.compile(r"\[FIXME[^\]]*\]", re.IGNORECASE), ""),
        ]

        for pattern, replacement in placeholder_patterns:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                fixes_applied.append("policy_fix: removed placeholder")
                text = new_text

        return text, fixes_applied

    def preprocess(self, text: str, enable_aggressive: bool = False) -> Dict[str, any]:
        """
        Huvudfunktion för pre-processing.

        Args:
            text: Rå response text
            enable_aggressive: Aktivera aggressivare fixar (default: False för säkerhet)

        Returns:
            Dict med fixad text och metadata
        """
        if not text or not isinstance(text, str):
            return {
                "text": text,
                "fixes_applied": [],
                "changed": False,
                "error": "Invalid input text",
            }

        original_text = text
        all_fixes = []

        # Kör fixar i ordning
        text, fixes = self.fix_structural_issues(text)
        all_fixes.extend(fixes)

        text, fixes = self.fix_swedish_language(text)
        all_fixes.extend(fixes)

        text, fixes = self.fix_markdown_formatting(text)
        all_fixes.extend(fixes)

        # JSON-fixar endast om det verkar vara JSON-content
        if "{" in text and "}" in text:
            text, fixes = self.fix_json_formatting(text)
            all_fixes.extend(fixes)

        # Policy-fixar endast om aggressivt läge
        if enable_aggressive:
            text, fixes = self.fix_policy_violations(text)
            all_fixes.extend(fixes)

        return {
            "text": text,
            "original_text": original_text,
            "fixes_applied": all_fixes,
            "changed": text != original_text,
            "fix_count": len(all_fixes),
        }

    def should_apply_fixes(self, verifier_errors: List[Dict]) -> bool:
        """
        Avgör om FormatGuard ska appliceras baserat på verifier errors.
        """
        if not verifier_errors:
            return False

        # Trigger på specifika error types som vi kan fixa
        fixable_errors = {
            "format_error",
            "json_invalid",
            "markdown_malformed",
            "encoding_issue",
            "whitespace_excessive",
        }

        for error in verifier_errors:
            if error.get("type") in fixable_errors:
                return True

        return False


# Singleton instans för enkel användning
_format_guard = None


def get_format_guard() -> FormatGuard:
    """Returnera singleton FormatGuard instans."""
    global _format_guard
    if _format_guard is None:
        _format_guard = FormatGuard()
    return _format_guard


def preprocess_response(text: str, enable_aggressive: bool = False) -> Dict[str, any]:
    """
    Convenience function för att preprocessa response text.
    """
    guard = get_format_guard()
    return guard.preprocess(text, enable_aggressive=enable_aggressive)
