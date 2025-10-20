#!/usr/bin/env python3
"""
README Audit Script

Analyzes all README.md files in the wepppy repository and generates a report
identifying which files would benefit from revision according to the new
README authoring standards.

Usage:
    python tools/audit_readmes.py [--output report.md] [--verbose]
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class ReadmeMetrics:
    """Metrics for evaluating README quality."""
    path: Path
    line_count: int = 0
    has_title: bool = False
    has_overview: bool = False
    has_see_also: bool = False
    has_code_example: bool = False
    has_api_docs: bool = False
    has_architecture: bool = False
    has_testing: bool = False
    has_troubleshooting: bool = False
    sections: List[str] = field(default_factory=list)
    quality_score: int = 0
    
    def calculate_score(self) -> int:
        """Calculate quality score (0-100)."""
        score = 0
        
        # Basic requirements (40 points)
        if self.has_title:
            score += 10
        if self.has_overview:
            score += 15
        if self.has_code_example:
            score += 15
        
        # Medium importance (30 points)
        if self.has_see_also:
            score += 10
        if self.has_api_docs:
            score += 10
        if self.line_count >= 50:
            score += 10
        
        # Nice to have (30 points)
        if self.has_architecture:
            score += 10
        if self.has_testing:
            score += 10
        if self.has_troubleshooting:
            score += 10
        
        self.quality_score = score
        return score


def find_readme_files(root_dir: Path) -> List[Path]:
    """Find all README.md files in the repository."""
    readme_files = []
    
    for pattern in ["README.md", "readme.md"]:
        readme_files.extend(root_dir.rglob(pattern))
    
    # Sort by path for consistent ordering
    return sorted(set(readme_files))


def analyze_readme(path: Path) -> ReadmeMetrics:
    """Analyze a README file and extract metrics."""
    metrics = ReadmeMetrics(path=path)
    
    try:
        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')
        metrics.line_count = len([l for l in lines if l.strip()])
        
        # Check for title (first line starting with #)
        for line in lines[:5]:
            if line.strip().startswith('#') and not line.strip().startswith('##'):
                metrics.has_title = True
                break
        
        # Extract sections
        section_pattern = re.compile(r'^#+\s+(.+)$')
        for line in lines:
            match = section_pattern.match(line.strip())
            if match:
                metrics.sections.append(match.group(1))
        
        # Check for key sections
        content_lower = content.lower()
        metrics.has_overview = 'overview' in content_lower or 'purpose' in content_lower
        metrics.has_see_also = 'see also' in content_lower and 'agents.md' in content_lower
        
        # Check for code examples (fenced code blocks)
        metrics.has_code_example = '```' in content
        
        # Check for specific sections
        metrics.has_api_docs = any(s.lower() in ['api', 'usage', 'api reference', 'usage / api reference'] 
                                   for s in metrics.sections)
        metrics.has_architecture = any('architecture' in s.lower() or 'design' in s.lower() 
                                       for s in metrics.sections)
        metrics.has_testing = any('test' in s.lower() for s in metrics.sections)
        metrics.has_troubleshooting = any('troubleshoot' in s.lower() for s in metrics.sections)
        
        # Calculate quality score
        metrics.calculate_score()
        
    except Exception as e:
        print(f"Error analyzing {path}: {e}")
    
    return metrics


def categorize_readme(metrics: ReadmeMetrics) -> str:
    """Categorize README quality for reporting."""
    if metrics.quality_score >= 80:
        return "excellent"
    elif metrics.quality_score >= 60:
        return "good"
    elif metrics.quality_score >= 40:
        return "needs-improvement"
    else:
        return "critical"


def generate_report(readme_metrics: List[ReadmeMetrics], output_path: Path = None) -> str:
    """Generate markdown report of README audit."""
    
    # Categorize READMEs
    excellent = [m for m in readme_metrics if categorize_readme(m) == "excellent"]
    good = [m for m in readme_metrics if categorize_readme(m) == "good"]
    needs_improvement = [m for m in readme_metrics if categorize_readme(m) == "needs-improvement"]
    critical = [m for m in readme_metrics if categorize_readme(m) == "critical"]
    
    report_lines = [
        "# README Audit Report",
        "",
        f"**Generated:** {Path.cwd().name} repository",
        f"**Total README files analyzed:** {len(readme_metrics)}",
        "",
        "## Summary",
        "",
        f"- ✅ **Excellent** (80-100 points): {len(excellent)} files",
        f"- ✔️ **Good** (60-79 points): {len(good)} files",
        f"- ⚠️ **Needs Improvement** (40-59 points): {len(needs_improvement)} files",
        f"- ❌ **Critical** (0-39 points): {len(critical)} files",
        "",
        "## Scoring Criteria",
        "",
        "README files are scored on a 100-point scale:",
        "",
        "**Basic Requirements (40 points):**",
        "- Has title: 10 points",
        "- Has overview: 15 points",
        "- Has code example: 15 points",
        "",
        "**Medium Importance (30 points):**",
        "- Links to AGENTS.md: 10 points",
        "- Documents APIs: 10 points",
        "- Substantial content (≥50 lines): 10 points",
        "",
        "**Nice to Have (30 points):**",
        "- Architecture section: 10 points",
        "- Testing section: 10 points",
        "- Troubleshooting section: 10 points",
        "",
    ]
    
    # Add detailed sections for each category
    def add_category_section(title: str, emoji: str, metrics_list: List[ReadmeMetrics]):
        if not metrics_list:
            return
        
        report_lines.extend([
            f"## {emoji} {title}",
            "",
            f"**Count:** {len(metrics_list)} files",
            "",
            "| Path | Score | Lines | Has Title | Has Example | Has Overview | Has See Also |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        
        for m in sorted(metrics_list, key=lambda x: x.quality_score):
            rel_path = str(m.path.relative_to(Path.cwd()))
            report_lines.append(
                f"| `{rel_path}` | {m.quality_score} | {m.line_count} | "
                f"{'✓' if m.has_title else '✗'} | "
                f"{'✓' if m.has_code_example else '✗'} | "
                f"{'✓' if m.has_overview else '✗'} | "
                f"{'✓' if m.has_see_also else '✗'} |"
            )
        
        report_lines.append("")
    
    add_category_section("Critical - Requires Immediate Attention", "❌", critical)
    add_category_section("Needs Improvement", "⚠️", needs_improvement)
    add_category_section("Good", "✔️", good)
    add_category_section("Excellent", "✅", excellent)
    
    # Recommendations section
    report_lines.extend([
        "## Recommendations",
        "",
        "### High Priority Actions",
        "",
    ])
    
    if critical:
        report_lines.extend([
            "1. **Critical READMEs** — These files need immediate attention:",
            "",
        ])
        for m in critical[:5]:  # Top 5 worst
            rel_path = str(m.path.relative_to(Path.cwd()))
            report_lines.append(f"   - `{rel_path}` (score: {m.quality_score})")
            missing = []
            if not m.has_title:
                missing.append("title")
            if not m.has_overview:
                missing.append("overview")
            if not m.has_code_example:
                missing.append("code example")
            if not m.has_see_also:
                missing.append("AGENTS.md link")
            if missing:
                report_lines.append(f"     - Missing: {', '.join(missing)}")
        report_lines.append("")
    
    if needs_improvement:
        report_lines.extend([
            "2. **Improvement Candidates** — These would benefit from enhancement:",
            "",
        ])
        for m in needs_improvement[:5]:  # Top 5
            rel_path = str(m.path.relative_to(Path.cwd()))
            report_lines.append(f"   - `{rel_path}` (score: {m.quality_score})")
        report_lines.append("")
    
    report_lines.extend([
        "### Suggested Actions",
        "",
        "1. **Use the template** — Copy `docs/templates/README_TEMPLATE.md` for new READMEs",
        "2. **Add examples** — Include at least one working code snippet",
        "3. **Link to AGENTS.md** — Add 'See also' reference at the top",
        "4. **Document APIs** — List key classes, functions, and their purposes",
        "5. **Add architecture** — Explain design patterns and integration points",
        "",
        "### Best Practices",
        "",
        "- Start with the header and overview",
        "- Add one working example minimum",
        "- Document the most commonly used APIs first",
        "- Link to related documentation instead of duplicating",
        "- Keep content current as code evolves",
        "",
        "## References",
        "",
        "- **Template:** `docs/templates/README_TEMPLATE.md`",
        "- **Guide:** `docs/README_AUTHORING_GUIDE.md`",
        "- **AGENTS.md:** Project-wide conventions and patterns",
        "",
    ])
    
    report = '\n'.join(report_lines)
    
    if output_path:
        output_path.write_text(report, encoding='utf-8')
        print(f"Report written to: {output_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Audit README files in wepppy repository"
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('docs/README_AUDIT_REPORT.md'),
        help='Output file for the report (default: docs/README_AUDIT_REPORT.md)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print detailed progress'
    )
    
    args = parser.parse_args()
    
    # Find and analyze all README files
    root = Path.cwd()
    print(f"Scanning repository: {root}")
    
    readme_files = find_readme_files(root)
    print(f"Found {len(readme_files)} README files")
    
    if args.verbose:
        print("\nAnalyzing files...")
    
    metrics = []
    for readme_path in readme_files:
        if args.verbose:
            print(f"  {readme_path.relative_to(root)}")
        metrics.append(analyze_readme(readme_path))
    
    # Generate report
    print(f"\nGenerating report...")
    report = generate_report(metrics, args.output)
    
    # Print summary
    excellent = sum(1 for m in metrics if categorize_readme(m) == "excellent")
    good = sum(1 for m in metrics if categorize_readme(m) == "good")
    needs_improvement = sum(1 for m in metrics if categorize_readme(m) == "needs-improvement")
    critical = sum(1 for m in metrics if categorize_readme(m) == "critical")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Excellent:         {excellent:3d} files")
    print(f"✔️ Good:              {good:3d} files")
    print(f"⚠️ Needs Improvement: {needs_improvement:3d} files")
    print(f"❌ Critical:          {critical:3d} files")
    print(f"{'='*60}")
    print(f"\nFull report available at: {args.output}")


if __name__ == '__main__':
    main()
