"""
Evaluation Report Generation

Generate comprehensive evaluation reports with all metrics.
"""

from typing import Dict
from datetime import datetime
import json
import csv
from pathlib import Path

from sqlalchemy.orm import Session

from spendsense.eval.metrics import (
    calculate_coverage,
    calculate_explainability,
    calculate_auditability,
    calculate_consent_enforcement,
    calculate_latency_metrics,
    calculate_eligibility_compliance,
    calculate_tone_compliance,
    calculate_relevance
)
from spendsense.ingest.schema import User, Recommendation, DecisionTrace


def generate_evaluation_report(session: Session) -> Dict:
    """
    Generate comprehensive evaluation report.
    
    Collects all metrics and formats into report structure.
    
    Returns:
        Dictionary containing all metrics and statistics
    """
    # Calculate all metrics
    coverage = calculate_coverage(session)
    explainability = calculate_explainability(session)
    auditability = calculate_auditability(session)
    consent_enforcement = calculate_consent_enforcement(session)
    latency = calculate_latency_metrics(session)
    eligibility_compliance = calculate_eligibility_compliance(session)
    tone_compliance = calculate_tone_compliance(session)
    relevance = calculate_relevance(session)
    
    # Get user statistics
    total_users = session.query(User).count()
    users_with_consent = session.query(User).filter(User.consent_status == True).count()
    users_with_recs = session.query(User).join(Recommendation).distinct().count()
    
    # Get users by persona (simplified - would need persona history query)
    users_by_persona = {}
    
    # Get recommendation statistics
    total_recommendations = session.query(Recommendation).count()
    
    recommendations_by_type = {}
    recommendations_by_status = {}
    recommendations_by_persona = {}
    
    for rec in session.query(Recommendation).all():
        # By type
        rec_type = rec.recommendation_type
        recommendations_by_type[rec_type] = recommendations_by_type.get(rec_type, 0) + 1
        
        # By status
        rec_status = rec.status or "pending"
        recommendations_by_status[rec_status] = recommendations_by_status.get(rec_status, 0) + 1
        
        # By persona
        rec_persona = rec.persona or "none"
        recommendations_by_persona[rec_persona] = recommendations_by_persona.get(rec_persona, 0) + 1
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "coverage": coverage.get("coverage_percent", 0),
            "explainability": explainability.get("explainability_percent", 0),
            "auditability": auditability.get("auditability_percent", 0),
            "consent_enforcement": consent_enforcement.get("compliant", False),
            "latency": latency,
            "eligibility_compliance": eligibility_compliance.get("compliance_percent", 0),
            "tone_compliance": tone_compliance.get("compliance_percent", 0),
            "relevance": relevance.get("relevance_percent", 0)
        },
        "detailed_metrics": {
            "coverage": coverage,
            "explainability": explainability,
            "auditability": auditability,
            "consent_enforcement": consent_enforcement,
            "latency": latency,
            "eligibility_compliance": eligibility_compliance,
            "tone_compliance": tone_compliance,
            "relevance": relevance
        },
        "user_stats": {
            "total_users": total_users,
            "users_with_consent": users_with_consent,
            "users_with_recommendations": users_with_recs,
            "users_by_persona": users_by_persona
        },
        "recommendation_stats": {
            "total_recommendations": total_recommendations,
            "by_type": recommendations_by_type,
            "by_status": recommendations_by_status,
            "by_persona": recommendations_by_persona
        },
        "per_user_decision_traces": _get_all_decision_traces(session)
    }
    
    return report


def _get_all_decision_traces(session: Session) -> Dict:
    """
    Get all decision traces organized by user.
    
    Returns:
        Dictionary mapping user_id to list of decision traces
    """
    traces_by_user = {}
    
    # Get all recommendations with their traces
    recommendations = session.query(Recommendation).all()
    
    for rec in recommendations:
        trace = session.query(DecisionTrace).filter(
            DecisionTrace.recommendation_id == rec.recommendation_id
        ).first()
        
        if trace:
            trace_dict = {
                "recommendation_id": rec.recommendation_id,
                "trace_id": trace.trace_id,
                "input_signals": trace.input_signals,
                "persona_assigned": trace.persona_assigned,
                "persona_reasoning": trace.persona_reasoning,
                "template_used": trace.template_used,
                "variables_inserted": trace.variables_inserted,
                "eligibility_checks": trace.eligibility_checks,
                "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
                "version": trace.version
            }
            
            if rec.user_id not in traces_by_user:
                traces_by_user[rec.user_id] = []
            
            traces_by_user[rec.user_id].append(trace_dict)
    
    return traces_by_user


def export_report_json(report: Dict, filepath: str) -> None:
    """Export report as JSON file."""
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)


def export_report_csv(report: Dict, filepath: str) -> None:
    """Export report as CSV file."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(["Metric", "Value"])
        
        # Write summary metrics
        writer.writerow(["Coverage (%)", report["summary"]["coverage"]])
        writer.writerow(["Explainability (%)", report["summary"]["explainability"]])
        writer.writerow(["Auditability (%)", report["summary"]["auditability"]])
        writer.writerow(["Consent Enforcement", report["summary"]["consent_enforcement"]])
        writer.writerow(["Eligibility Compliance (%)", report["summary"]["eligibility_compliance"]])
        writer.writerow(["Tone Compliance (%)", report["summary"]["tone_compliance"]])
        writer.writerow(["Relevance (%)", report["summary"]["relevance"]])
        
        # Write user stats
        writer.writerow([])
        writer.writerow(["User Statistics"])
        writer.writerow(["Total Users", report["user_stats"]["total_users"]])
        writer.writerow(["Users with Consent", report["user_stats"]["users_with_consent"]])
        writer.writerow(["Users with Recommendations", report["user_stats"]["users_with_recommendations"]])
        
        # Write recommendation stats
        writer.writerow([])
        writer.writerow(["Recommendation Statistics"])
        writer.writerow(["Total Recommendations", report["recommendation_stats"]["total_recommendations"]])
        
        writer.writerow([])
        writer.writerow(["By Type"])
        for rec_type, count in report["recommendation_stats"]["by_type"].items():
            writer.writerow([rec_type, count])
        
        writer.writerow([])
        writer.writerow(["By Status"])
        for status, count in report["recommendation_stats"]["by_status"].items():
            writer.writerow([status, count])


def export_decision_traces_json(traces_by_user: Dict, filepath: str) -> None:
    """Export per-user decision traces as JSON file."""
    with open(filepath, 'w') as f:
        json.dump(traces_by_user, f, indent=2, default=str)


def export_report_html(report: Dict, filepath: str) -> None:
    """Export report as HTML file."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SpendSense Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #34495e; color: white; }}
        .metric {{ margin: 10px 0; }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #2c3e50; }}
    </style>
</head>
<body>
    <h1>SpendSense Evaluation Report</h1>
    <p><strong>Generated:</strong> {report['timestamp']}</p>
    
    <h2>Summary Metrics</h2>
    <div class="metric">
        <strong>Coverage:</strong> <span class="metric-value">{report['summary']['coverage']:.1f}%</span>
    </div>
    <div class="metric">
        <strong>Explainability:</strong> <span class="metric-value">{report['summary']['explainability']:.1f}%</span>
    </div>
    <div class="metric">
        <strong>Auditability:</strong> <span class="metric-value">{report['summary']['auditability']:.1f}%</span>
    </div>
    <div class="metric">
        <strong>Consent Enforcement:</strong> <span class="metric-value">{'✓ PASS' if report['summary']['consent_enforcement'] else '✗ FAIL'}</span>
    </div>
    <div class="metric">
        <strong>Eligibility Compliance:</strong> <span class="metric-value">{report['summary']['eligibility_compliance']:.1f}%</span>
    </div>
        <div class="metric">
            <strong>Tone Compliance:</strong> <span class="metric-value">{report['summary']['tone_compliance']:.1f}%</span>
        </div>
        <div class="metric">
            <strong>Relevance:</strong> <span class="metric-value">{report['summary']['relevance']:.1f}%</span>
        </div>
    
    <h2>User Statistics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Users</td><td>{report['user_stats']['total_users']}</td></tr>
        <tr><td>Users with Consent</td><td>{report['user_stats']['users_with_consent']}</td></tr>
        <tr><td>Users with Recommendations</td><td>{report['user_stats']['users_with_recommendations']}</td></tr>
    </table>
    
    <h2>Recommendation Statistics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Recommendations</td><td>{report['recommendation_stats']['total_recommendations']}</td></tr>
    </table>
    
    <h3>By Type</h3>
    <table>
        <tr><th>Type</th><th>Count</th></tr>
        {"".join(f"<tr><td>{rec_type}</td><td>{count}</td></tr>" for rec_type, count in report['recommendation_stats']['by_type'].items())}
    </table>
    
    <h3>By Status</h3>
    <table>
        <tr><th>Status</th><th>Count</th></tr>
        {"".join(f"<tr><td>{status}</td><td>{count}</td></tr>" for status, count in report['recommendation_stats']['by_status'].items())}
    </table>
    
    <h2>Detailed Metrics</h2>
    <pre>{json.dumps(report['detailed_metrics'], indent=2, default=str)}</pre>
</body>
</html>
"""
    
    with open(filepath, 'w') as f:
        f.write(html_content)


def print_summary(report: Dict) -> None:
    """Print summary of report to console."""
    print("\n" + "="*60)
    print("SPENDSENSE EVALUATION REPORT")
    print("="*60)
    print(f"Generated: {report['timestamp']}\n")
    
    print("SUMMARY METRICS:")
    print(f"  Coverage: {report['summary']['coverage']:.1f}%")
    print(f"  Explainability: {report['summary']['explainability']:.1f}%")
    print(f"  Auditability: {report['summary']['auditability']:.1f}%")
    print(f"  Consent Enforcement: {'✓ PASS' if report['summary']['consent_enforcement'] else '✗ FAIL'}")
    print(f"  Eligibility Compliance: {report['summary']['eligibility_compliance']:.1f}%")
    print(f"  Tone Compliance: {report['summary']['tone_compliance']:.1f}%")
    print(f"  Relevance: {report['summary']['relevance']:.1f}%")
    
    print("\nUSER STATISTICS:")
    print(f"  Total Users: {report['user_stats']['total_users']}")
    print(f"  Users with Consent: {report['user_stats']['users_with_consent']}")
    print(f"  Users with Recommendations: {report['user_stats']['users_with_recommendations']}")
    
    print("\nRECOMMENDATION STATISTICS:")
    print(f"  Total Recommendations: {report['recommendation_stats']['total_recommendations']}")
    print(f"  By Type: {report['recommendation_stats']['by_type']}")
    print(f"  By Status: {report['recommendation_stats']['by_status']}")
    print("="*60 + "\n")


def main():
    """CLI entry point for generating evaluation report."""
    from spendsense.ingest.database import get_session
    
    session = get_session()
    try:
        report = generate_evaluation_report(session)
        
        # Export to JSON
        export_report_json(report, "evaluation_report.json")
        print("✓ Exported evaluation_report.json")
        
        # Export to CSV
        export_report_csv(report, "evaluation_report.csv")
        print("✓ Exported evaluation_report.csv")
        
        # Export to HTML
        export_report_html(report, "evaluation_report.html")
        print("✓ Exported evaluation_report.html")
        
        # Export per-user decision traces to JSON
        export_decision_traces_json(report["per_user_decision_traces"], "per_user_decision_traces.json")
        print("✓ Exported per_user_decision_traces.json")
        
        # Print summary to console
        print_summary(report)
    finally:
        session.close()


if __name__ == "__main__":
    main()

