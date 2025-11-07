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


# Practice Session Schemas
class PracticeSessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PracticeSessionBase(BaseModel):
    playbook_id: int
    symbol: str
    initial_balance: Optional[float] = 100000.0


class PracticeSessionCreate(PracticeSessionBase):
    playbook_data: Optional[Dict[str, Any]] = None


class PracticeSessionUpdate(BaseModel):
    current_step: Optional[int] = None
    status: Optional[PracticeSessionStatus] = None
    current_balance: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class PracticeSessionResponse(PracticeSessionBase):
    id: int
    user_id: int
    playbook_data: Optional[Dict[str, Any]] = None
    status: PracticeSessionStatus
    current_step: int
    initial_balance: float
    current_balance: float
    performance_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trades: List["PracticeTradeResponse"] = []

    class Config:
        from_attributes = True


# Practice Trade Schemas
class PracticeTradeBase(BaseModel):
    trade_type: TradeType
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class PracticeTradeCreate(PracticeTradeBase):
    step_number: int


class PracticeTradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    status: Optional[TradeStatus] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None


class PracticeTradeResponse(PracticeTradeBase):
    id: int
    session_id: int
    step_number: int
    exit_price: Optional[float] = None
    status: TradeStatus
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Update PracticeSessionResponse to include trades (forward reference)
PracticeSessionResponse.model_rebuild()


# Step Completion Schemas
class StepCompletionRequest(BaseModel):
    step_number: int
    actions_taken: Optional[Dict[str, Any]] = None  # Track what user did in this step


class StepCompletionResponse(BaseModel):
    step_number: int
    completed: bool
    feedback: Optional[str] = None
    next_step: Optional[int] = None
    is_final_step: bool = False


# Trade Execution Schemas
class TradeExecutionRequest(BaseModel):
    trade_type: TradeType
    symbol: str
    quantity: float
    entry_price: Optional[float] = None  # None = market order (use current price)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeExecutionResponse(BaseModel):
    trade_id: int
    trade_type: TradeType
    symbol: str
    quantity: float
    entry_price: float
    status: TradeStatus
    current_balance: float
    message: str


# Performance Metrics Schema
class PerformanceMetrics(BaseModel):
    total_pnl: float
    total_pnl_percentage: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    max_drawdown: Optional[float] = None
    current_balance: float
    initial_balance: float


# Playbook Schemas
class PlaybookStep(BaseModel):
    step: int
    title: str
    description: str
    details: str


class PlaybookBase(BaseModel):
    title: str
    description: str
    category: str
    level: CourseLevel
    icon: str
    steps: List[PlaybookStep]


class PlaybookCreate(PlaybookBase):
    pass


class PlaybookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[CourseLevel] = None
    icon: Optional[str] = None
    steps: Optional[List[PlaybookStep]] = None


class PlaybookResponse(PlaybookBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed: Optional[bool] = None  # User-specific completion status

    class Config:
        from_attributes = True
