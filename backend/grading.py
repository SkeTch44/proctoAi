import json
import logging 
from typing  import Dict, Any, List,Tuple
from sentence_transformers import SentenceTransformer, util
import numpy as np

logger = logging.getLogger(__name__)
class GradingEngine:
    """
    Automated grading engine supporting multiple questionn types:
     - Multiple Choice Questions (MCQ)
     - True/False Questions 
     - Short Answer Questions
     -Fill in the Blanks Questions 
     - Matching 
     - Essay 
     Uses semetic similarity (Sentence Transformers ) for open ended responses
     and  rule- based for closed ended types.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-V2'):
                       try:
                               self.sim_model = SentenceTransformer(model_name)
                               logger.info(f"Loaded semantic model: {model_name}")
                            
                       except Exception as e:    
                               logger.error(f"Failed to load semantic model: {e}")
                               self.sim_model =  None 
    def grade_exam(self,questions: List [Dict[str ,Any]], answers: Dict[str,any]) -> dict[str,any]:
            """
            Grade a full  exam , 
            questions: list of questions 
            dicts(id,type,points,etc.)
            answer: mapping from question id (str) to user answer 
            Return summary with 
            total_score, max_score, details per questin.
            """                


            total_score = 0.0 
            max_score = 0.0
            details = []

            for q in questions:
                qid = str(q.get('id'))
                max_points = q.get('points',1)
                max_score += max_points
                user_ans = answers.get(qid,None)


                score, feedback = self.grade_question (q, user_ans)
                total_score += score 
                details.append({'id':qid,
                                'type':q.get('type'),
                                'max_points': max_points,
                                'score': score,
                                'feedback': feedback
                            
                            })     
            percentage = (total_score/max_score*100) if max_score else 0  
            return{
                        'total_score' : total_score,
                        'max_score' : max_score,
                        'percentage': round(percentage,2),
                        'details': details
                }
                    

                
              

    def grade_question(self, question: Dict[str, Any], answer: Any) -> Tuple[float, str]:
        """
        Grade an individual question based on its type. Returns (score, feedback).
        """
        qtype = question.get('type')
        if qtype == 'mcq':
            return self._grade_mcq(question, answer)
        if qtype == 'true_false':
               return self._grade_true_false(question,answer)
        if qtype == 'short_answer':
               return self._grade_short_answer(question,answer)
        if qtype == 'fill_blanks':
               return self._grade_fill_blanks(question,answer)
        if qtype == 'essay':
               return self._grade_essay(question,answer)
        
        # default fallback
        return 0.0, "unsupported question type "
    
    def _grade_mcq(self, q: Dict, ans : str ) -> Tuple [float,str]:
           correct = q.get ('correct_answer', '').strip().upper()
           user = (ans or '').strip().upper()
           if user == correct:
                  return q.get('points',1), "correct"
           return 0.0 , f"incorrect.Correct answer: {correct}."
    
    def _grade_true_false(self,q:Dict, ans :Any) -> Tuple[float,str]:
           correct = bool(q.get('correct_answer', False))
           user = True if str  (ans).lower() in ['true', 't' , '1', 'yes'] else False
           if user == correct:
                  return q.get ('points',1),"correct."
           return 0.0, f"Incorrect.Correct answer: {correct}."
    def _grade_short_answer(self,q:Dict, ans: str) -> Tuple[float,str]:
           sample = q.get ('sample_answer', '')
           if not sample or not ans :
                  return 0.0, "NO sample answer or user answer provided"           
           if self.sim_model:
                  
                  score = util.pytorch_cos_sim(
                         *self.sim_model.encode([sample, ans], convert_to_tensor=True)).item()  
                  normalized = min(max(score,0.0),1.0)
                  points = normalized*q.get ('points',2)
                  feedback = f"similarity : {normalized:.2f}"
                  return round(points, 2),feedback
           

           #fallback keywords 
           overlap = len(set(sample.lower().split()) & set (ans.lower().split()))
           ratio = overlap/ max(len(sample.split()),1)
           points = ratio * q.get('points',2)
           feedback = f"Keyword match: {ratio:.2f}"
           return round(points , 2),feedback
    def _grade_fill_blanks(self,q:Dict,ans : Any) -> tuple[float,str]:
           correct = [b.lower() for b in q.get('blanks', [])]
           user = [u.strip().lower () for u in (ans or [])]
           if not correct or not user :
                  return 0.0, "NO blanks or answers provided "
           right = sum (1 for u , c in zip(user,correct) if u == c) 
           ratio = right / len(correct)
           points = ratio*q.get('points',1)
           feedback = f"{right}/{len(correct)}correct"
           return round(points,2 ),feedback
    
    def _grade_essay(self, q:Dict , ans: str) -> Tuple[float,str]:
           sample = q.get('sample_answer','')
           if not ans:
                  return 0.0 , "NO answer provided" 
                # length check (20% of score )    
           words = len(ans.split())
           ideal_length = q.get('ideal_length', 200)  
           length_score = min(words / 200, 1.0) * 0.2
# sematic check (80 % of score )
           
           sem_score = 0.0 
           if self.sim_model and sample :
            try :
                sem = util.pytorch_cos_sim(
                        *self.sim_model.encode([sample, ans], convert_to_tensor=True)).item()  
                sem_score = min(max(sem, 0.0),1.0) * 0.8
            except Exception as e:
                logger.warning(f"Semantic model error: {e}")
           total = (length_score + sem_score) * q.get('points', 5)     
           feedback = f"Length component: {length_score:.2f}, Semantic: {sem_score:.2f}"  
           return round(total, 2), feedback

                

                
                      
               
                  
                
           

