#!/usr/bin/env python3
"""
Generate build health page from CI/CD artifacts.

This script:
1. Parses coverage.xml for coverage metrics
2. Parses pytest-junit.xml for test results
3. Fetches recent GitHub Actions runs
4. Generates HTML build health dashboard
5. Outputs to docs/index.html for GitHub Pages

Usage:
    python scripts/generate-build-health.py
    python scripts/generate-build-health.py --output docs/index.html
"""

import argparse
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import requests, but make it optional
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests library not installed. GitHub API features disabled.")


def parse_coverage_xml(coverage_file: str = "coverage.xml") -> Dict[str, Any]:
    """
    Parse coverage.xml and extract metrics.

    Returns:
        dict with keys: line_rate, branch_rate, lines_covered, lines_valid,
        branches_covered, branches_valid, timestamp
    """
    if not Path(coverage_file).exists():
        return {
            "line_rate": 0.0,
            "branch_rate": 0.0,
            "lines_covered": 0,
            "lines_valid": 0,
            "branches_covered": 0,
            "branches_valid": 0,
            "timestamp": None,
            "percentage": 0.0,
        }

    tree = ET.parse(coverage_file)
    root = tree.getroot()

    line_rate = float(root.attrib.get("line-rate", 0))
    branch_rate = float(root.attrib.get("branch-rate", 0))
    lines_covered = int(root.attrib.get("lines-covered", 0))
    lines_valid = int(root.attrib.get("lines-valid", 0))
    branches_covered = int(root.attrib.get("branches-covered", 0))
    branches_valid = int(root.attrib.get("branches-valid", 0))
    timestamp = root.attrib.get("timestamp")

    return {
        "line_rate": line_rate,
        "branch_rate": branch_rate,
        "lines_covered": lines_covered,
        "lines_valid": lines_valid,
        "branches_covered": branches_covered,
        "branches_valid": branches_valid,
        "timestamp": timestamp,
        "percentage": round(line_rate * 100, 2),
        "branch_percentage": round(branch_rate * 100, 2),
    }


def parse_junit_xml(junit_file: str = "pytest-junit.xml") -> Dict[str, Any]:
    """
    Parse pytest-junit.xml and extract test results.

    Returns:
        dict with keys: tests, failures, errors, skipped, time
    """
    if not Path(junit_file).exists():
        return {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "time": 0.0,
            "passed": 0,
        }

    tree = ET.parse(junit_file)
    root = tree.getroot()

    # JUnit XML can have <testsuites> or <testsuite> as root
    if root.tag == "testsuites":
        testsuite = root.find("testsuite")
        if testsuite is None:
            testsuite = root
    else:
        testsuite = root

    tests = int(testsuite.attrib.get("tests", 0))
    failures = int(testsuite.attrib.get("failures", 0))
    errors = int(testsuite.attrib.get("errors", 0))
    skipped = int(testsuite.attrib.get("skipped", 0))
    time = float(testsuite.attrib.get("time", 0))

    passed = tests - failures - errors - skipped

    return {
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "time": round(time, 2),
        "passed": passed,
    }


def fetch_github_runs(
    repo: str = "FreeSideNomad/reckie-langchain",
    branch: str = "main",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch recent GitHub Actions runs via API.

    Requires GITHUB_TOKEN environment variable for authentication.

    Returns:
        list of dicts with keys: id, status, conclusion, created_at, updated_at
    """
    if not HAS_REQUESTS:
        return []

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. Skipping GitHub API calls.")
        return []

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{repo}/actions/runs"
    params = {
        "branch": branch,
        "per_page": limit,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        runs = []
        for run in data.get("workflow_runs", []):
            runs.append({
                "id": run["id"],
                "name": run["name"],
                "status": run["status"],
                "conclusion": run["conclusion"],
                "created_at": run["created_at"],
                "updated_at": run["updated_at"],
                "html_url": run["html_url"],
            })

        return runs
    except Exception as e:
        print(f"Error fetching GitHub runs: {e}")
        return []


def generate_html(
    coverage: Dict[str, Any],
    tests: Dict[str, Any],
    runs: List[Dict[str, Any]],
) -> str:
    """Generate HTML for build health page."""

    # Determine build status
    if tests["failures"] > 0 or tests["errors"] > 0:
        build_status = "failing"
        status_color = "#dc3545"
        status_icon = "❌"
    elif coverage["percentage"] < 85:
        build_status = "warning"
        status_color = "#ffc107"
        status_icon = "⚠️"
    else:
        build_status = "passing"
        status_color = "#28a745"
        status_icon = "✅"

    # Format timestamp
    if coverage["timestamp"]:
        try:
            ts = int(coverage["timestamp"]) / 1000
            dt = datetime.fromtimestamp(ts)
            last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            last_updated = "Unknown"
    else:
        last_updated = "Unknown"

    # Generate history table HTML
    history_rows = ""
    for run in runs[:10]:
        conclusion_emoji = {
            "success": "✅",
            "failure": "❌",
            "cancelled": "🚫",
            "skipped": "⏭️",
        }.get(run.get("conclusion"), "⏳")

        created = run.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created_fmt = dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_fmt = created
        else:
            created_fmt = "Unknown"

        history_rows += f"""
        <tr>
            <td><a href="{run['html_url']}" target="_blank">#{run['id']}</a></td>
            <td>{run['name']}</td>
            <td>{conclusion_emoji} {run.get('conclusion', 'running')}</td>
            <td>{created_fmt}</td>
        </tr>
        """

    if not history_rows:
        history_rows = "<tr><td colspan='4'>No build history available</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Health - LangChain Demo</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f6f8fa;
            color: #24292e;
            line-height: 1.6;
            padding: 2rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}

        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            color: #24292e;
        }}

        .subtitle {{
            color: #586069;
            font-size: 1rem;
        }}

        .status-badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 1.1rem;
            margin-top: 1rem;
            background: {status_color};
            color: white;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .metric-label {{
            font-size: 0.875rem;
            color: #586069;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #24292e;
        }}

        .metric-detail {{
            font-size: 0.875rem;
            color: #586069;
            margin-top: 0.5rem;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e1e4e8;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 1rem;
        }}

        .progress-fill {{
            height: 100%;
            background: {status_color};
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }}

        .section {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}

        h2 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: #24292e;
            border-bottom: 2px solid #e1e4e8;
            padding-bottom: 0.5rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            text-align: left;
            padding: 0.75rem;
            background: #f6f8fa;
            font-weight: 600;
            color: #24292e;
            border-bottom: 2px solid #e1e4e8;
        }}

        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #e1e4e8;
        }}

        tr:hover {{
            background: #f6f8fa;
        }}

        a {{
            color: #0366d6;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .timestamp {{
            text-align: right;
            color: #586069;
            font-size: 0.875rem;
            margin-top: 2rem;
        }}

        .coverage-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-top: 1rem;
        }}

        .coverage-item {{
            padding: 1rem;
            background: #f6f8fa;
            border-radius: 6px;
        }}

        .coverage-item strong {{
            display: block;
            margin-bottom: 0.5rem;
            color: #24292e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{status_icon} Build Health Dashboard</h1>
            <p class="subtitle">LangChain Document Management System</p>
            <div class="status-badge">Build Status: {build_status.upper()}</div>
        </header>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Code Coverage</div>
                <div class="metric-value">{coverage['percentage']}%</div>
                <div class="metric-detail">
                    {coverage['lines_covered']}/{coverage['lines_valid']} lines covered<br>
                    Branch: {coverage['branch_percentage']}%
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {coverage['percentage']}%">
                        {coverage['percentage']}%
                    </div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Tests Passed</div>
                <div class="metric-value">{tests['passed']}/{tests['tests']}</div>
                <div class="metric-detail">
                    Failures: {tests['failures']}<br>
                    Errors: {tests['errors']}<br>
                    Skipped: {tests['skipped']}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Test Duration</div>
                <div class="metric-value">{tests['time']}s</div>
                <div class="metric-detail">
                    Last run completed successfully
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Coverage Details</h2>
            <div class="coverage-details">
                <div class="coverage-item">
                    <strong>Line Coverage</strong>
                    <div>{coverage['lines_covered']} / {coverage['lines_valid']} lines ({coverage['percentage']}%)</div>
                </div>
                <div class="coverage-item">
                    <strong>Branch Coverage</strong>
                    <div>{coverage['branches_covered']} / {coverage['branches_valid']} branches ({coverage['branch_percentage']}%)</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Recent Builds</h2>
            <table>
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Workflow</th>
                        <th>Status</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
        </div>

        <div class="timestamp">
            Last updated: {last_updated}
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate build health page")
    parser.add_argument(
        "--coverage",
        default="coverage.xml",
        help="Path to coverage.xml file",
    )
    parser.add_argument(
        "--junit",
        default="pytest-junit.xml",
        help="Path to pytest-junit.xml file",
    )
    parser.add_argument(
        "--output",
        default="docs/index.html",
        help="Output HTML file path",
    )
    parser.add_argument(
        "--repo",
        default="FreeSideNomad/reckie-langchain",
        help="GitHub repository (owner/repo)",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch to track",
    )

    args = parser.parse_args()

    print("📊 Generating build health page...")

    # Parse coverage
    print(f"  Reading coverage from: {args.coverage}")
    coverage = parse_coverage_xml(args.coverage)
    print(f"  ✓ Coverage: {coverage['percentage']}%")

    # Parse test results
    print(f"  Reading test results from: {args.junit}")
    tests = parse_junit_xml(args.junit)
    print(f"  ✓ Tests: {tests['passed']}/{tests['tests']} passed")

    # Fetch GitHub runs
    print(f"  Fetching GitHub Actions runs...")
    runs = fetch_github_runs(args.repo, args.branch)
    print(f"  ✓ Found {len(runs)} recent runs")

    # Generate HTML
    html = generate_html(coverage, tests, runs)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"✅ Build health page generated: {args.output}")
    print(f"   Coverage: {coverage['percentage']}%")
    print(f"   Tests: {tests['passed']}/{tests['tests']} passing")


if __name__ == "__main__":
    main()
