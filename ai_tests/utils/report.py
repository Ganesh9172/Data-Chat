import json
import time
from pathlib import Path
from typing import List, Dict, Any
from ai_tests.config import REPORTS_DIR

class TestReportCollector:
    """
    Collects individual test outcomes across categories and formats
    comprehensive terminal, markdown, and JSON reports.
    """
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def record(
        self,
        category: str,
        question: str,
        expected: str,
        actual: str,
        passed: bool,
        reason: str = "",
        screenshot: str = ""
    ):
        self.results.append({
            "category": category,
            "question": question,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "reason": reason,
            "screenshot": screenshot,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    def print_summary(self):
        total = len(self.results)
        passed_count = sum(1 for r in self.results if r["passed"])
        failed_count = total - passed_count

        # Group by category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if r["passed"]:
                categories[cat]["passed"] += 1

        category_labels = {
            "knowledge": "Knowledge",
            "natural_language": "Natural Language",
            "general_questions": "General Questions",
            "followup": "Follow-up",
            "out_of_scope": "Out of Scope",
            "citations": "Citations",
            "basic": "Basic UI"
        }

        print("\n" + "=" * 80)
        print("FIREBIRD AI TEST REPORT")
        print(f"Total: {total}  Passed: {passed_count}  Failed: {failed_count}")
        print("-" * 80)
        for cat, stats in categories.items():
            label = category_labels.get(cat, cat.replace("_", " ").title())
            print(f"{label}: {stats['passed']}/{stats['total']}")
        print("=" * 80)

        # Print failures
        failures = [r for r in self.results if not r["passed"]]
        if failures:
            print("\nFAILURES:")
            for f in failures:
                print(f"Question: {f['question']}")
                print(f"Expected: {f['expected']}")
                print(f"Actual: {f['actual']}")
                print(f"Result: FAIL")
                print(f"Reason: {f['reason']}")
                if f.get("screenshot"):
                    print(f"Screenshot: {f['screenshot']}")
                print("-" * 40)
        print()

    def save_reports(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        json_path = REPORTS_DIR / "test_report.json"
        md_path = REPORTS_DIR / "test_report.md"

        # 1. JSON Report
        total = len(self.results)
        passed_count = sum(1 for r in self.results if r["passed"])
        failed_count = total - passed_count

        report_data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": total,
            "passed": passed_count,
            "failed": failed_count,
            "results": self.results
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # 2. Markdown Report
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if r["passed"]:
                categories[cat]["passed"] += 1

        md_lines = [
            "# Firebird AI Automated Test Report",
            f"\n**Generated at:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Total Tests:** {total} | **Passed:** {passed_count} | **Failed:** {failed_count}\n",
            "## Category Summary\n",
            "| Category | Passed | Total | Rate |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for cat, stats in categories.items():
            rate = f"{(stats['passed'] / max(1, stats['total'])) * 100:.1f}%"
            md_lines.append(f"| {cat.replace('_', ' ').title()} | {stats['passed']} | {stats['total']} | {rate} |")

        md_lines.append("\n## Detailed Test Results\n")
        md_lines.append("| Status | Category | Question | Reason |")
        md_lines.append("| :--- | :--- | :--- | :--- |")

        for r in self.results:
            status = "PASS" if r["passed"] else "FAIL"
            q = r["question"].replace("|", "\\|")
            reason = r["reason"].replace("|", "\\|")
            md_lines.append(f"| {status} | {r['category']} | {q} | {reason} |")

        failures = [r for r in self.results if not r["passed"]]
        if failures:
            md_lines.append("\n## Failure Details\n")
            for f in failures:
                md_lines.append(f"### Question: `{f['question']}`")
                md_lines.append(f"- **Expected:** {f['expected']}")
                md_lines.append(f"- **Actual:** {f['actual']}")
                md_lines.append(f"- **Reason:** {f['reason']}")
                if f.get("screenshot"):
                    md_lines.append(f"- **Screenshot:** `{f['screenshot']}`")
                md_lines.append("")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print(f"[Reports Saved] -> {json_path} and {md_path}")

# Global singleton collector for pytest session
global_report_collector = TestReportCollector()
