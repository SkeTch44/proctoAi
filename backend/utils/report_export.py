"""
Report Export Utility
Generates exam reports in various formats (PDF, JSON, etc.)
"""

import json
import io
from typing import Dict, Any, List, Optional
from datetime import datetime

# ReportLab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.lib.units import inch
    reportlab_available = True
except ImportError:
    reportlab_available = False


def generate_exam_report(exam_data: Dict[str, Any], format_type: str = 'json') -> Any:
    """
    Generate an exam report in the specified format.
    
    Args:
        exam_data: Dictionary containing exam results and metadata
        format_type: Output format ('json', 'text', 'pdf')
    
    Returns:
        Formatted report (string for json/text, bytes for pdf)
    """
    if format_type == 'json':
        return json.dumps(exam_data, indent=2)
    
    elif format_type == 'text':
        return _generate_text_report(exam_data)
        
    elif format_type == 'pdf':
        if not reportlab_available:
            raise ImportError("ReportLab is not installed. Cannot generate PDF.")
        return _generate_pdf_report(exam_data)
    
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


def _generate_text_report(exam_data: Dict[str, Any]) -> str:
    report = []
    report.append("=" * 50)
    report.append("EXAM REPORT")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    if 'exam_title' in exam_data:
        report.append(f"Exam: {exam_data['exam_title']}")
    if 'student_name' in exam_data:
        report.append(f"Student: {exam_data['student_name']}")
    if 'score' in exam_data:
        report.append(f"Score: {exam_data['score']}")
    if 'suspicion_score' in exam_data:
        report.append(f"Suspicion Score: {exam_data['suspicion_score']}")
    
    report.append("=" * 50)
    return "\n".join(report)



def _add_answer_log(story, styles, exam_data):
    """Helper to add detailed answer log to the PDF story"""
    story.append(Spacer(1, 24))
    story.append(Paragraph("Detailed Answer Log", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    questions = exam_data.get('questions', [])
    answers = exam_data.get('answers', {})
    grading_details = exam_data.get('grading_details', [])
    
    # Create a map for quick lookup of grading details
    grade_map = {d['id']: d for d in grading_details}
    
    for i, q in enumerate(questions, 1):
        qid = str(q.get('id'))
        q_text = q.get('question', 'Question text missing')
        user_ans = answers.get(qid, 'No answer provided')
        grade_info = grade_map.get(qid, {})
        
        # Question Header
        story.append(Paragraph(f"Q{i}: {q_text}", styles['Heading3']))
        
        # Details Table
        score = grade_info.get('score', 0)
        max_points = q.get('points', 1)
        feedback = grade_info.get('feedback', '')
        
        data = [
            ["User Answer", Paragraph(str(user_ans), styles['Normal'])],
            ["Score", f"{score} / {max_points}"],
            ["Feedback", Paragraph(str(feedback), styles['Normal'])]
        ]
        
        t = Table(data, colWidths=[1.5*inch, 4.5*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

def _generate_pdf_report(exam_data: Dict[str, Any]) -> bytes:
    """Generate PDF report bytes using ReportLab"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("ProctoAi Exam Report", styles['Title']))
    story.append(Spacer(1, 12))

    # Metadata Table
    data = [
        ["Exam Title", exam_data.get('exam_title', 'N/A')],
        ["Student", exam_data.get('student_name', 'N/A')],
        ["Date", datetime.now().strftime('%Y-%m-%d %H:%M')],
        ["Score", f"{exam_data.get('score', 0)}"],
        ["Suspicion Score", f"{exam_data.get('suspicion_score', 0)}/100"]
    ]
    
    t = Table(data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 24))

    # Suspicion Analysis Chart
    story.append(Paragraph("Session Suspicion Analysis", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    events = exam_data.get('events', [])
    if not events:
        story.append(Paragraph("No proctoring events recorded.", styles['Normal']))
    else:
        event_data = [["Time", "Type", "Severity", "Impact"]]
        for e in events[:20]: # Limit to 20 events
            event_data.append([
                e.get('timestamp', '')[11:19], # HH:MM:SS
                e.get('alert_type', 'Unknown'),
                e.get('severity', 'Low'),
                str(e.get('score_impact', 0))
            ])
            
        t_events = Table(event_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch])
        t_events.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(t_events)

    # Detailed Answer Log
    _add_answer_log(story, styles, exam_data)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_proctoring_report(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a proctoring report for a session.
    """
    return {
        "session_id": session_data.get("session_id"),
        "total_events": len(session_data.get("events", [])),
        "suspicion_score": session_data.get("suspicion_score", 0),
        "high_severity_events": [
            e for e in session_data.get("events", [])
            if e.get("severity") in ["high", "critical"]
        ],
        "timestamp": datetime.now().isoformat()
    }
