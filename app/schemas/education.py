from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from enum import Enum


class LessonType(str, Enum):
    DESCRIPTION = "description"


class CourseLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


# Lesson Schemas
class LessonBase(BaseModel):
    title: str
    duration: str
    type: LessonType
    content: Optional[str] = None
    order: int


class LessonCreate(LessonBase):
    course_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    duration: Optional[str] = None
    type: Optional[LessonType] = None
    content: Optional[str] = None
    order: Optional[int] = None


class LessonResponse(LessonBase):
    id: int
    course_id: int
    completed: Optional[bool] = False  # User-specific completion status
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Course Schemas
class CourseBase(BaseModel):
    title: str
    description: str
    level: CourseLevel
    duration: str
    modules: int
    category: str
    instructor: str
    icon: str


class CourseCreate(CourseBase):
    lessons: List[LessonBase] = []


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[CourseLevel] = None
    duration: Optional[str] = None
    modules: Optional[int] = None
    category: Optional[str] = None
    instructor: Optional[str] = None
    icon: Optional[str] = None


class CourseResponse(CourseBase):
    id: int
    progress: Optional[int] = 0  # User-specific progress percentage
    lessons: List[LessonResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Progress Schemas
class CourseProgressResponse(BaseModel):
    course_id: int
    progress: int
    completed_lessons: int
    total_lessons: int


# Quiz Schemas
class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple-choice"
    TRUE_FALSE = "true-false"
    MULTIPLE_SELECT = "multiple-select"


class QuestionBase(BaseModel):
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    correct_answer: Union[int, bool, List[int]]  # int for multiple-choice index, bool for true-false, List[int] for multiple-select
    order: int
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionResponse(BaseModel):
    id: int
    quiz_id: int
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[int, bool, List[int]]] = None  # Optional - hidden in quiz list
    order: int
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str


class QuizCreate(QuizBase):
    questions: List[QuestionBase] = []


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class QuizResponse(QuizBase):
    id: int
    questions: List[QuestionResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    best_score: Optional[int] = None  # User's best score if authenticated
    attempts_count: Optional[int] = None  # Number of attempts by user

    class Config:
        from_attributes = True


class QuizSubmission(BaseModel):
    answers: Dict[int, Union[int, bool, List[int]]]  # question_id -> user_answer


class QuizResult(BaseModel):
    quiz_id: int
    score: int
    total_questions: int
    percentage: int
    answers: Dict[int, Union[int, bool, List[int]]]  # question_id -> user_answer
    question_results: Dict[int, bool]  # question_id -> is_correct
    correct_answers: Dict[int, Union[int, bool, List[int]]]  # question_id -> correct_answer
    completed_at: datetime


class QuizAttemptHistory(BaseModel):
    id: int
    quiz_id: int
    quiz_title: str
    score: int
    total_questions: int
    percentage: int
    completed_at: datetime

    class Config:
        from_attributes = True
