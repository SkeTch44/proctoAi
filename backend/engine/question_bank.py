
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import re

logger = logging.getLogger(__name__)

class QuestionDifficulty(Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

class QuestionType(Enum):
    """Supported question types"""
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    TRUE_FALSE = "true_false"
    FILL_BLANKS = "fill_blanks"
    MATCHING = "matching"
    ORDERING = "ordering"
    NUMERICAL = "numerical"

class QuestionStatus(Enum):
    """Question status"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"

@dataclass
class Question:
    """Question data model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    title: str = ""
    question_text: str = ""
    question_type: str = QuestionType.MCQ.value
    difficulty: str = QuestionDifficulty.MEDIUM.value
    points: int = 1
    time_limit: Optional[int] = None  # seconds
    subject: str = ""
    topic: str = ""
    subtopic: str = ""
    learning_objective: str = ""
    bloom_level: str = "knowledge"
    question_data: Dict = None
    explanation: str = ""
    hints: List[str] = None
    tags: List[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: str = QuestionStatus.DRAFT.value
    usage_count: int = 0
    average_score: float = 0.0
    difficulty_rating: float = 0.0
    version: int = 1
    parent_id: Optional[int] = None  # For question versions
    
    def __post_init__(self):
        if self.uuid is None:
            self.uuid = str(uuid.uuid4())
        if self.question_data is None:
            self.question_data = {}
        if self.hints is None:
            self.hints = []
        if self.tags is None:
            self.tags = []

@dataclass
class QuestionBank:
    """Question bank data model"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    subject: str = ""
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_public: bool = False
    is_template: bool = False
    tags: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

class QuestionBankManager:
    """
    Comprehensive Question Bank Management System
    
    Features:
    - Question CRUD operations with versioning
    - Advanced search and filtering
    - Question bank organization
    - Import/Export functionality
    - Analytics and statistics
    - Question validation and quality checks
    - Collaboration features
    - Template management
    """
    
    def __init__(self, db_path: str = "exam_platform.db"):
        self.db_path = db_path
        self.init_database()
        logger.info("QuestionBankManager initialized")
    
    def init_database(self):
        """Initialize question bank database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Question banks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    subject TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_public BOOLEAN DEFAULT FALSE,
                    is_template BOOLEAN DEFAULT FALSE,
                    tags TEXT,
                    metadata TEXT,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Enhanced questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    title TEXT,
                    question_text TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'medium',
                    points INTEGER DEFAULT 1,
                    time_limit INTEGER,
                    subject TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    learning_objective TEXT,
                    bloom_level TEXT DEFAULT 'knowledge',
                    question_data TEXT NOT NULL,
                    explanation TEXT,
                    hints TEXT,
                    tags TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'draft',
                    usage_count INTEGER DEFAULT 0,
                    average_score REAL DEFAULT 0.0,
                    difficulty_rating REAL DEFAULT 0.0,
                    version INTEGER DEFAULT 1,
                    parent_id INTEGER,
                    content_hash TEXT,
                    FOREIGN KEY (created_by) REFERENCES users (id),
                    FOREIGN KEY (parent_id) REFERENCES questions (id)
                )
            ''')
            
            # Question bank items (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_bank_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    order_index INTEGER DEFAULT 0,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by INTEGER,
                    weight REAL DEFAULT 1.0,
                    is_mandatory BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (bank_id) REFERENCES question_banks (id) ON DELETE CASCADE,
                    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
                    FOREIGN KEY (added_by) REFERENCES users (id),
                    UNIQUE(bank_id, question_id)
                )
            ''')
            
            # Question categories
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    description TEXT,
                    subject TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES question_categories (id)
                )
            ''')
            
            # Question reviews and ratings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    difficulty_rating INTEGER CHECK(difficulty_rating >= 1 AND difficulty_rating <= 5),
                    quality_rating INTEGER CHECK(quality_rating >= 1 AND quality_rating <= 5),
                    comments TEXT,
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
                    FOREIGN KEY (reviewer_id) REFERENCES users (id),
                    UNIQUE(question_id, reviewer_id)
                )
            ''')
            
            # Question usage statistics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    exam_id INTEGER,
                    session_id INTEGER,
                    student_answer TEXT,
                    is_correct BOOLEAN,
                    score REAL,
                    time_taken INTEGER,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
                )
            ''')
            
            # Question templates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS question_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    question_type TEXT NOT NULL,
                    template_data TEXT NOT NULL,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_public BOOLEAN DEFAULT FALSE,
                    usage_count INTEGER DEFAULT 0,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_uuid ON questions(uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_created_by ON questions(created_by)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_parent_id ON questions(parent_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_question_banks_created_by ON question_banks(created_by)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_question_bank_items_bank_id ON question_bank_items(bank_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_question_bank_items_question_id ON question_bank_items(question_id)')
            
            conn.commit()
            logger.info("Question bank database initialized successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            conn.close()
    
    # ==================== QUESTION CRUD OPERATIONS ====================
    
    def create_question(self, question: Question) -> Optional[int]:
        """Create a new question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(question)
            
            cursor.execute('''
                INSERT INTO questions (
                    uuid, title, question_text, question_type, difficulty, points,
                    time_limit, subject, topic, subtopic, learning_objective,
                    bloom_level, question_data, explanation, hints, tags,
                    created_by, status, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question.uuid, question.title, question.question_text,
                question.question_type, question.difficulty, question.points,
                question.time_limit, question.subject, question.topic,
                question.subtopic, question.learning_objective, question.bloom_level,
                json.dumps(question.question_data), question.explanation,
                json.dumps(question.hints), json.dumps(question.tags),
                question.created_by, question.status, content_hash
            ))
            
            question_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Question created with ID: {question_id}")
            return question_id
            
        except sqlite3.IntegrityError as e:
            if "uuid" in str(e):
                logger.error("Question with this UUID already exists")
            else:
                logger.error(f"Question creation failed: {e}")
            return None
        except Exception as e:
            conn.rollback()
            logger.error(f"Question creation failed: {e}")
            return None
        finally:
            conn.close()
    
    def bulk_create_questions(self, questions: List[Question], bank_id: int = None) -> Dict[str, Any]:
        """
        Bulk create multiple questions in a single transaction.
        
        Args:
            questions: List of Question objects to create
            bank_id: Optional bank ID to add all questions to
            
        Returns:
            Dict with 'created_count', 'failed_count', 'question_ids'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_ids = []
        failed_count = 0
        
        try:
            for question in questions:
                try:
                    content_hash = self._generate_content_hash(question)
                    
                    cursor.execute('''
                        INSERT INTO questions (
                            uuid, title, question_text, question_type, difficulty, points,
                            time_limit, subject, topic, subtopic, learning_objective,
                            bloom_level, question_data, explanation, hints, tags,
                            created_by, status, content_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        question.uuid, question.title, question.question_text,
                        question.question_type, question.difficulty, question.points,
                        question.time_limit, question.subject, question.topic,
                        question.subtopic, question.learning_objective, question.bloom_level,
                        json.dumps(question.question_data), question.explanation,
                        json.dumps(question.hints), json.dumps(question.tags),
                        question.created_by, question.status, content_hash
                    ))
                    
                    question_id = cursor.lastrowid
                    created_ids.append(question_id)
                    
                    # Add to bank if specified
                    if bank_id and question_id:
                        cursor.execute('''
                            INSERT OR IGNORE INTO question_bank_items (bank_id, question_id, added_by)
                            VALUES (?, ?, ?)
                        ''', (bank_id, question_id, question.created_by))
                        
                except sqlite3.IntegrityError as e:
                    logger.warning(f"Duplicate question skipped: {e}")
                    failed_count += 1
                except Exception as e:
                    logger.error(f"Failed to create question: {e}")
                    failed_count += 1
            
            conn.commit()
            logger.info(f"Bulk created {len(created_ids)} questions, {failed_count} failed")
            
            return {
                'created_count': len(created_ids),
                'failed_count': failed_count,
                'question_ids': created_ids
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Bulk creation failed: {e}")
            return {
                'created_count': 0,
                'failed_count': len(questions),
                'question_ids': [],
                'error': str(e)
            }
        finally:
            conn.close()
    
    def get_question(self, question_id: int) -> Optional[Question]:
        """Get a question by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_question(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get question {question_id}: {e}")
            return None
        finally:
            conn.close()
    
    def get_question_by_uuid(self, question_uuid: str) -> Optional[Question]:
        """Get a question by UUID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM questions WHERE uuid = ?', (question_uuid,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_question(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get question {question_uuid}: {e}")
            return None
        finally:
            conn.close()
    
    def update_question(self, question_id: int, updates: Dict) -> bool:
        """Update a question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            
            allowed_fields = [
                'title', 'question_text', 'question_type', 'difficulty', 'points',
                'time_limit', 'subject', 'topic', 'subtopic', 'learning_objective',
                'bloom_level', 'question_data', 'explanation', 'hints', 'tags', 'status'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field in ['question_data', 'hints', 'tags']:
                        value = json.dumps(value)
                    set_clauses.append(f'{field} = ?')
                    values.append(value)
            
            if not set_clauses:
                logger.warning("No valid fields to update")
                return False
            
            # Add updated_at
            set_clauses.append('updated_at = CURRENT_TIMESTAMP')
            
            query = f'UPDATE questions SET {", ".join(set_clauses)} WHERE id = ?'
            values.append(question_id)
            
            cursor.execute(query, values)
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Question {question_id} updated successfully")
                return True
            else:
                logger.warning(f"Question {question_id} not found")
                return False
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Question update failed: {e}")
            return False
        finally:
            conn.close()
    
    def delete_question(self, question_id: int, user_id: int) -> bool:
        """Delete a question (soft delete by setting status to archived)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check ownership or admin privileges
            cursor.execute('''
                SELECT created_by FROM questions WHERE id = ?
            ''', (question_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Question {question_id} not found")
                return False
            
            # For now, allow deletion by creator or admin (you'd check user role)
            # In production, add proper authorization
            
            # Soft delete
            cursor.execute('''
                UPDATE questions 
                SET status = 'archived', updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (question_id,))
            
            conn.commit()
            
            logger.info(f"Question {question_id} archived by user {user_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Question deletion failed: {e}")
            return False
        finally:
            conn.close()
    
    def duplicate_question(self, question_id: int, user_id: int) -> Optional[int]:
        """Create a duplicate of an existing question"""
        original = self.get_question(question_id)
        if not original:
            return None
        
        # Create a copy with new UUID and creator
        duplicate = Question(
            title=f"Copy of {original.title}",
            question_text=original.question_text,
            question_type=original.question_type,
            difficulty=original.difficulty,
            points=original.points,
            time_limit=original.time_limit,
            subject=original.subject,
            topic=original.topic,
            subtopic=original.subtopic,
            learning_objective=original.learning_objective,
            bloom_level=original.bloom_level,
            question_data=original.question_data.copy(),
            explanation=original.explanation,
            hints=original.hints.copy(),
            tags=original.tags.copy(),
            created_by=user_id,
            status=QuestionStatus.DRAFT.value
        )
        
        return self.create_question(duplicate)
    
    # ==================== QUESTION SEARCH AND FILTERING ====================
    
    def search_questions(self, 
                        user_id: int,
                        query: str = None,
                        filters: Dict = None,
                        page: int = 1,
                        per_page: int = 20) -> Dict:
        """Advanced question search with filtering and pagination"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build search query
            where_conditions = []
            params = []
            
            # Base condition: user can see their own questions or public ones
            where_conditions.append("(created_by = ? OR status = 'active')")
            params.append(user_id)
            
            # Text search
            if query:
                where_conditions.append("""
                    (title LIKE ? OR question_text LIKE ? OR subject LIKE ? OR topic LIKE ? OR tags LIKE ?)
                """)
                search_term = f"%{query}%"
                params.extend([search_term] * 5)
            
            # Filters
            if filters:
                if filters.get('question_type'):
                    where_conditions.append("question_type = ?")
                    params.append(filters['question_type'])
                
                if filters.get('difficulty'):
                    where_conditions.append("difficulty = ?")
                    params.append(filters['difficulty'])
                
                if filters.get('subject'):
                    where_conditions.append("subject = ?")
                    params.append(filters['subject'])
                
                if filters.get('topic'):
                    where_conditions.append("topic = ?")
                    params.append(filters['topic'])
                
                if filters.get('status'):
                    where_conditions.append("status = ?")
                    params.append(filters['status'])
                
                if filters.get('bloom_level'):
                    where_conditions.append("bloom_level = ?")
                    params.append(filters['bloom_level'])
                
                if filters.get('points_min'):
                    where_conditions.append("points >= ?")
                    params.append(filters['points_min'])
                
                if filters.get('points_max'):
                    where_conditions.append("points <= ?")
                    params.append(filters['points_max'])
                
                if filters.get('tags'):
                    tags_condition = []
                    for tag in filters['tags']:
                        tags_condition.append("tags LIKE ?")
                        params.append(f"%{tag}%")
                    if tags_condition:
                        where_conditions.append(f"({' OR '.join(tags_condition)})")
            
            # Build complete query
            where_clause = " AND ".join(where_conditions)
            
            # Count total results
            count_query = f"SELECT COUNT(*) FROM questions WHERE {where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            offset = (page - 1) * per_page
            
            main_query = f"""
                SELECT * FROM questions 
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(main_query, params + [per_page, offset])
            rows = cursor.fetchall()
            
            questions = [self._row_to_question(row) for row in rows]
            
            # Calculate pagination info
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'questions': [asdict(q) for q in questions],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Question search failed: {e}")
            return {'questions': [], 'pagination': {}}
        finally:
            conn.close()
    
    def get_question_statistics(self, user_id: int = None) -> Dict:
        """Get question statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Base query condition
            where_condition = "WHERE 1=1"
            params = []
            
            if user_id:
                where_condition += " AND created_by = ?"
                params.append(user_id)
            
            # Total questions
            cursor.execute(f"SELECT COUNT(*) FROM questions {where_condition}", params)
            stats['total_questions'] = cursor.fetchone()[0]
            
            # Questions by type
            cursor.execute(f"""
                SELECT question_type, COUNT(*) 
                FROM questions {where_condition}
                GROUP BY question_type
            """, params)
            stats['by_type'] = dict(cursor.fetchall())
            
            # Questions by difficulty
            cursor.execute(f"""
                SELECT difficulty, COUNT(*) 
                FROM questions {where_condition}
                GROUP BY difficulty
            """, params)
            stats['by_difficulty'] = dict(cursor.fetchall())
            
            # Questions by status
            cursor.execute(f"""
                SELECT status, COUNT(*) 
                FROM questions {where_condition}
                GROUP BY status
            """, params)
            stats['by_status'] = dict(cursor.fetchall())
            
            # Questions by subject
            cursor.execute(f"""
                SELECT subject, COUNT(*) 
                FROM questions {where_condition}
                GROUP BY subject
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, params)
            stats['by_subject'] = dict(cursor.fetchall())
            
            # Most used questions
            cursor.execute(f"""
                SELECT title, usage_count 
                FROM questions {where_condition}
                ORDER BY usage_count DESC
                LIMIT 10
            """, params)
            stats['most_used'] = [{'title': title, 'usage_count': count} 
                                for title, count in cursor.fetchall()]
            
            # Average ratings
            cursor.execute(f"""
                SELECT AVG(average_score) as avg_score, AVG(difficulty_rating) as avg_difficulty
                FROM questions {where_condition}
                WHERE usage_count > 0
            """, params)
            
            row = cursor.fetchone()
            stats['average_score'] = round(row[0] or 0, 2)
            stats['average_difficulty'] = round(row[1] or 0, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get question statistics: {e}")
            return {}
        finally:
            conn.close()
    
    # ==================== QUESTION BANK OPERATIONS ====================
    
    def create_question_bank(self, bank: QuestionBank) -> Optional[int]:
        """Create a new question bank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO question_banks (
                    name, description, subject, created_by, is_public, is_template, tags, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bank.name, bank.description, bank.subject, bank.created_by,
                bank.is_public, bank.is_template, json.dumps(bank.tags),
                json.dumps(bank.metadata)
            ))
            
            bank_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Question bank created with ID: {bank_id}")
            return bank_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Question bank creation failed: {e}")
            return None
        finally:
            conn.close()
    
    def add_question_to_bank(self, bank_id: int, question_id: int, user_id: int, 
                           order_index: int = 0, weight: float = 1.0, is_mandatory: bool = False) -> bool:
        """Add a question to a question bank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO question_bank_items (
                    bank_id, question_id, order_index, added_by, weight, is_mandatory
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (bank_id, question_id, order_index, user_id, weight, is_mandatory))
            
            conn.commit()
            
            logger.info(f"Question {question_id} added to bank {bank_id}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Question {question_id} already exists in bank {bank_id}")
            return False
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add question to bank: {e}")
            return False
        finally:
            conn.close()
    
    def remove_question_from_bank(self, bank_id: int, question_id: int) -> bool:
        """Remove a question from a question bank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM question_bank_items 
                WHERE bank_id = ? AND question_id = ?
            ''', (bank_id, question_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Question {question_id} removed from bank {bank_id}")
                return True
            else:
                logger.warning(f"Question {question_id} not found in bank {bank_id}")
                return False
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to remove question from bank: {e}")
            return False
        finally:
            conn.close()
    
    def get_question_bank(self, bank_id: int) -> Optional[Dict]:
        """Get a question bank with its questions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get bank details
            cursor.execute('SELECT * FROM question_banks WHERE id = ?', (bank_id,))
            bank_row = cursor.fetchone()
            
            if not bank_row:
                return None
            
            # Get questions in the bank
            cursor.execute('''
                SELECT q.*, qbi.order_index, qbi.weight, qbi.is_mandatory
                FROM questions q
                JOIN question_bank_items qbi ON q.id = qbi.question_id
                WHERE qbi.bank_id = ?
                ORDER BY qbi.order_index, q.title
            ''', (bank_id,))
            
            question_rows = cursor.fetchall()
            
            # Build bank data
            bank_data = {
                'id': bank_row[0],
                'name': bank_row[1],
                'description': bank_row[2],
                'subject': bank_row[3],
                'created_by': bank_row[4],
                'created_at': bank_row[5],
                'updated_at': bank_row[6],
                'is_public': bool(bank_row[7]),
                'is_template': bool(bank_row[8]),
                'tags': json.loads(bank_row[9] or '[]'),
                'metadata': json.loads(bank_row[10] or '{}'),
                'questions': []
            }
            
            for row in question_rows:
                question_data = self._row_to_question(row[:len(row)-3])  # Exclude bank-specific fields
                question_dict = asdict(question_data)
                question_dict.update({
                    'order_index': row[-3],
                    'weight': row[-2],
                    'is_mandatory': bool(row[-1])
                })
                bank_data['questions'].append(question_dict)
            
            return bank_data
            
        except Exception as e:
            logger.error(f"Failed to get question bank {bank_id}: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_question_banks(self, user_id: int) -> List[Dict]:
        """Get all question banks for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT qb.*, COUNT(qbi.question_id) as question_count
                FROM question_banks qb
                LEFT JOIN question_bank_items qbi ON qb.id = qbi.bank_id
                WHERE qb.created_by = ? OR qb.is_public = 1
                GROUP BY qb.id
                ORDER BY qb.updated_at DESC
            ''', (user_id,))
            
            banks = []
            for row in cursor.fetchall():
                bank_data = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'subject': row[3],
                    'created_by': row[4],
                    'created_at': row[5],
                    'updated_at': row[6],
                    'is_public': bool(row[7]),
                    'is_template': bool(row[8]),
                    'tags': json.loads(row[9] or '[]'),
                    'metadata': json.loads(row[10] or '{}'),
                    'question_count': row[11]
                }
                banks.append(bank_data)
            
            return banks
            
        except Exception as e:
            logger.error(f"Failed to get user question banks: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== QUESTION VALIDATION ====================
    
    def validate_question(self, question: Question) -> Tuple[bool, List[str]]:
        """Validate question data and return validation result"""
        errors = []
        
        # Required fields
        if not question.question_text.strip():
            errors.append("Question text is required")
        
        if not question.question_type:
            errors.append("Question type is required")
        
        if question.points <= 0:
            errors.append("Points must be greater than 0")
        
        # Type-specific validations
        if question.question_type == QuestionType.MCQ.value:
            options = question.question_data.get('options', [])
            if len(options) < 2:
                errors.append("MCQ questions must have at least 2 options")
            
            correct_answer = question.question_data.get('correct_answer')
            if not correct_answer:
                errors.append("MCQ questions must have a correct answer")
        
        elif question.question_type == QuestionType.FILL_BLANKS.value:
            blanks = question.question_data.get('blanks', [])
            if not blanks:
                errors.append("Fill in the blanks questions must have at least one blank")
        
        elif question.question_type == QuestionType.MATCHING.value:
            pairs = question.question_data.get('matching_pairs', {})
            if len(pairs) < 2:
                errors.append("Matching questions must have at least 2 pairs")
        
        # Content validations
        if len(question.question_text) > 5000:
            errors.append("Question text is too long (max 5000 characters)")
        
        if question.subject and len(question.subject) > 100:
            errors.append("Subject is too long (max 100 characters)")
        
        if question.topic and len(question.topic) > 100:
            errors.append("Topic is too long (max 100 characters)")
        
        # Difficulty validation
        if question.difficulty not in [d.value for d in QuestionDifficulty]:
            errors.append(f"Invalid difficulty level: {question.difficulty}")
        
        # Bloom's taxonomy validation
        valid_bloom_levels = ['knowledge', 'comprehension', 'application', 'analysis', 'synthesis', 'evaluation']
        if question.bloom_level and question.bloom_level not in valid_bloom_levels:
            errors.append(f"Invalid Bloom's taxonomy level: {question.bloom_level}")
        
        return len(errors) == 0, errors
    
    def check_duplicate_question(self, question: Question, exclude_id: int = None) -> Optional[int]:
        """Check if a similar question already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            content_hash = self._generate_content_hash(question)
            
            query = "SELECT id FROM questions WHERE content_hash = ?"
            params = [content_hash]
            
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return None
        finally:
            conn.close()
    
    # ==================== IMPORT/EXPORT ====================
    
    def export_question_bank(self, bank_id: int, format_type: str = 'json') -> Optional[str]:
        """Export question bank in specified format"""
        bank_data = self.get_question_bank(bank_id)
        if not bank_data:
            return None
        
        try:
            if format_type.lower() == 'json':
                return json.dumps(bank_data, indent=2, ensure_ascii=False, default=str)
            
            elif format_type.lower() == 'csv':
                # Implementation for CSV export would go here
                pass
            
            elif format_type.lower() == 'qti':
                # Implementation for QTI format would go here
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None
    
    def import_question_bank(self, user_id: int, data: str, format_type: str = 'json') -> Optional[int]:
        """Import question bank from specified format"""
        try:
            if format_type.lower() == 'json':
                bank_data = json.loads(data)
                
                # Create new question bank
                bank = QuestionBank(
                    name=bank_data.get('name', 'Imported Bank'),
                    description=bank_data.get('description', ''),
                    subject=bank_data.get('subject', ''),
                    created_by=user_id,
                    tags=bank_data.get('tags', []),
                    metadata=bank_data.get('metadata', {})
                )
                
                bank_id = self.create_question_bank(bank)
                if not bank_id:
                    return None
                
                # Import questions
                for q_data in bank_data.get('questions', []):
                    question = Question(
                        title=q_data.get('title', ''),
                        question_text=q_data['question_text'],
                        question_type=q_data['question_type'],
                        difficulty=q_data.get('difficulty', 'medium'),
                        points=q_data.get('points', 1),
                        subject=q_data.get('subject', ''),
                        topic=q_data.get('topic', ''),
                        question_data=q_data.get('question_data', {}),
                        explanation=q_data.get('explanation', ''),
                        hints=q_data.get('hints', []),
                        tags=q_data.get('tags', []),
                        created_by=user_id
                    )
                    
                    question_id = self.create_question(question)
                    if question_id:
                        self.add_question_to_bank(bank_id, question_id, user_id)
                
                return bank_id
                
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return None
    
    # ==================== ANALYTICS ====================
    
    def record_question_usage(self, question_id: int, exam_id: int = None, 
                            session_id: int = None, student_answer: str = None,
                            is_correct: bool = None, score: float = None, 
                            time_taken: int = None) -> bool:
        """Record question usage for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Record usage stats
            cursor.execute('''
                INSERT INTO question_usage_stats (
                    question_id, exam_id, session_id, student_answer,
                    is_correct, score, time_taken
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_id, exam_id, session_id, student_answer, 
                  is_correct, score, time_taken))
            
            # Update question usage count and average score
            cursor.execute('''
                UPDATE questions 
                SET usage_count = usage_count + 1,
                    average_score = (
                        SELECT AVG(score) 
                        FROM question_usage_stats 
                        WHERE question_id = ? AND score IS NOT NULL
                    )
                WHERE id = ?
            ''', (question_id, question_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record question usage: {e}")
            return False
        finally:
            conn.close()
    
    def get_question_analytics(self, question_id: int) -> Dict:
        """Get analytics for a specific question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            analytics = {}
            
            # Basic usage stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN is_correct = 1 THEN 1 END) as correct_attempts,
                    AVG(score) as avg_score,
                    AVG(time_taken) as avg_time
                FROM question_usage_stats 
                WHERE question_id = ?
            ''', (question_id,))
            
            row = cursor.fetchone()
            if row:
                analytics.update({
                    'total_attempts': row[0],
                    'correct_attempts': row[1] or 0,
                    'success_rate': (row[1] or 0) / max(row[0], 1) * 100,
                    'average_score': round(row[2] or 0, 2),
                    'average_time': round(row[3] or 0, 1)
                })
            
            # Score distribution
            cursor.execute('''
                SELECT score, COUNT(*) 
                FROM question_usage_stats 
                WHERE question_id = ? AND score IS NOT NULL
                GROUP BY CAST(score AS INTEGER)
                ORDER BY score
            ''', (question_id,))
            
            analytics['score_distribution'] = dict(cursor.fetchall())
            
            # Recent performance trend (last 30 days)
            cursor.execute('''
                SELECT DATE(used_at) as date, AVG(score) as avg_score
                FROM question_usage_stats 
                WHERE question_id = ? 
                    AND used_at >= datetime('now', '-30 days')
                    AND score IS NOT NULL
                GROUP BY DATE(used_at)
                ORDER BY date
            ''', (question_id,))
            
            analytics['performance_trend'] = [
                {'date': row[0], 'avg_score': round(row[1], 2)}
                for row in cursor.fetchall()
            ]
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get question analytics: {e}")
            return {}
        finally:
            conn.close()
    
    # ==================== UTILITY METHODS ====================
    
    def _row_to_question(self, row) -> Question:
        """Convert database row to Question object"""
        return Question(
            id=row[0],
            uuid=row[1],
            title=row[2],
            question_text=row[3],
            question_type=row[4],
            difficulty=row[5],
            points=row[6],
            time_limit=row[7],
            subject=row[8],
            topic=row[9],
            subtopic=row[10],
            learning_objective=row[11],
            bloom_level=row[12],
            question_data=json.loads(row[13]) if row[13] else {},
            explanation=row[14],
            hints=json.loads(row[15]) if row[15] else [],
            tags=json.loads(row[16]) if row[16] else [],
            created_by=row[17],
            created_at=row[18],
            updated_at=row[19],
            status=row[20],
            usage_count=row[21],
            average_score=row[22],
            difficulty_rating=row[23],
            version=row[24],
            parent_id=row[25]
        )
    
    def _generate_content_hash(self, question: Question) -> str:
        """Generate content hash for duplicate detection"""
        content = f"{question.question_text}{question.question_type}{json.dumps(question.question_data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_subjects(self) -> List[str]:
        """Get list of all subjects"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT subject 
                FROM questions 
                WHERE subject IS NOT NULL AND subject != ''
                ORDER BY subject
            ''')
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get subjects: {e}")
            return []
        finally:
            conn.close()
    
    def get_topics_by_subject(self, subject: str) -> List[str]:
        """Get topics for a specific subject"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT topic 
                FROM questions 
                WHERE subject = ? AND topic IS NOT NULL AND topic != ''
                ORDER BY topic
            ''', (subject,))
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get topics for subject {subject}: {e}")
            return []
        finally:
            conn.close()
    
    def get_popular_tags(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get most popular tags with usage count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT tags FROM questions WHERE tags IS NOT NULL')
            
            tag_counts = {}
            for row in cursor.fetchall():
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Sort by count and return top tags
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_tags[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get popular tags: {e}")
            return []
        finally:
            conn.close()

# Export main class
__all__ = ['QuestionBankManager', 'Question', 'QuestionBank', 'QuestionType', 'QuestionDifficulty', 'QuestionStatus']







    