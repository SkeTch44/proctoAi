import unittest
import sys
import os
import io

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.report_export import generate_exam_report

class TestPDFGeneration(unittest.TestCase):
    def test_pdf_creation(self):
        """Test that PDF generation returns bytes and starts with PDF header"""
        exam_data = {
            'exam_title': 'Test Exam',
            'student_name': 'Test Student',
            'score': 85.5,
            'suspicion_score': 10,
            'events': [
                {'timestamp': '2026-01-17T10:00:00Z', 'alert_type': 'TEST', 'severity': 'LOW', 'score_impact': 0}
            ],
            'questions': [{'id': '1', 'question': 'Q1?', 'points': 1}],
            'answers': {'1': 'A1'},
            'grading_details': [{'id': '1', 'score': 1, 'feedback': 'Good'}]
        }
        
        pdf_bytes = generate_exam_report(exam_data, format_type='pdf')
        
        # Check if it's bytes
        self.assertIsInstance(pdf_bytes, bytes)
        
        # Check for PDF header (%PDF)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        print(f"\nPDF Generated. Size: {len(pdf_bytes)} bytes")

if __name__ == '__main__':
    unittest.main()
