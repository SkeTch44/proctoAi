
import sys
import os
import unittest
from datetime import datetime

# Adjust path to find backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.report_export import generate_exam_report

class TestReportGeneration(unittest.TestCase):
    def test_pdf_generation(self):
        # Mock session data
        mock_data = {
            'exam_title': 'Test Exam 101',
            'student_name': 'Test Student',
            'score': 85.5,
            'suspicion_score': 12,
            'events': [
                {'timestamp': '2026-01-20T10:00:00Z', 'alert_type': 'TAB_SWITCH', 'severity': 'low'},
                {'timestamp': '2026-01-20T10:05:00Z', 'alert_type': 'FACE_NOT_VISIBLE', 'severity': 'high'}
            ],
            'questions': [
                {'id': 'q1', 'question': 'What is AI?', 'points': 5},
                {'id': 'q2', 'question': 'Explain RAG.', 'points': 10}
            ],
            'answers': {
                'q1': 'Artificial Intelligence',
                'q2': 'Retrieval Augmented Generation'
            },
            'grading_details': [
                {'id': 'q1', 'score': 5, 'feedback': 'Correct'},
                {'id': 'q2', 'score': 8, 'feedback': 'Good explanation'}
            ]
        }
        
        print("\nGenerated Mock Data...")
        try:
            pdf_bytes = generate_exam_report(mock_data, format_type='pdf')
            print(f"PDF Generated. Size: {len(pdf_bytes)} bytes")
            
            # Verify PDF header
            self.assertTrue(pdf_bytes.startswith(b'%PDF'), "Output is not a valid PDF")
            
            # Verify content presence (simple check)
            self.assertGreater(len(pdf_bytes), 1000, "PDF seems too small")
            
        except Exception as e:
            self.fail(f"PDF Generation failed: {e}")

if __name__ == '__main__':
    unittest.main()
