
import unittest
import sys
import os
from datetime import datetime

# Add root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.report_export import generate_exam_report

class TestPDFExport(unittest.TestCase):
    def test_pdf_generation(self):
        """Test that PDF generation returns bytes and valid header"""
        exam_data = {
            'exam_title': 'Test Exam 101',
            'student_name': 'John Doe',
            'score': 85.5,
            'suspicion_score': 12,
            'events': [
                {'timestamp': '2023-01-01T10:00:00Z', 'alert_type': 'FACE_ABSENCE', 'severity': 'high', 'score_impact': 10},
                {'timestamp': '2023-01-01T10:05:00Z', 'alert_type': 'GAZE_DEVIATION', 'severity': 'low', 'score_impact': 2}
            ],
            'questions': [{'id': '1', 'question': 'Q1', 'points': 1}],
            'answers': {'1': 'A1'},
            'grading_details': [{'id': '1', 'score': 1, 'feedback': 'Good'}]
        }
        
        pdf_bytes = generate_exam_report(exam_data, format_type='pdf')
        
        # Check if bytes returned
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)
        
        # Basic check for PDF magic number
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

if __name__ == '__main__':
    unittest.main()
