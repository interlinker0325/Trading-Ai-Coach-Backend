from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum, UniqueConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class LessonType(str, enum.Enum):
    DESCRIPTION = "description"


class CourseLevel(str, enum.Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    # Persist enum VALUES (e.g., 'Beginner') to match SQL type 'course_level_enum'
    level = Column(
        Enum(
            CourseLevel,
            name="course_level_enum",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    duration = Column(String, nullable=False)  # e.g., "3h 20min"
    modules = Column(Integer, nullable=False)  # Number of lessons
    category = Column(String, nullable=False, index=True)  # Stocks, Options, Crypto, Futures, Forex
    instructor = Column(String, nullable=False)
    icon = Column(String, nullable=False)  # Icon name from lucide-react
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    user_progress = relationship("UserCourseProgress", back_populates="course", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    duration = Column(String, nullable=False)  # e.g., "15 min"
    # Persist enum VALUES (e.g., 'description') to match SQL type 'lesson_type_enum'
    type = Column(
        Enum(
            LessonType,
            name="lesson_type_enum",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    content = Column(Text, nullable=True)  # For description type lessons
    order = Column(Integer, nullable=False)  # Display order within course
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="lessons")
    user_progress = relationship("UserLessonProgress", back_populates="lesson", cascade="all, delete-orphan")


class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    progress = Column(Integer, default=0)  # Percentage 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="course_progress")
    course = relationship("Course", back_populates="user_progress")

    # Unique constraint: one progress record per user per course
    __table_args__ = (UniqueConstraint('user_id', 'course_id', name='uq_user_course_progress'),)


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="lesson_progress")
    lesson = relationship("Lesson", back_populates="user_progress")

    # Unique constraint: one progress record per user per lesson
    __table_args__ = (UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson_progress'),)


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple-choice"
    TRUE_FALSE = "true-false"
    MULTIPLE_SELECT = "multiple-select"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, index=True)  # Stocks, Options, Crypto, Futures, Forex
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order")
    user_attempts = relationship("UserQuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(
        Enum(
            QuestionType,
            name="question_type_enum",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    options = Column(JSON, nullable=True)  # Array of strings for multiple-choice/multiple-select
    correct_answer = Column(JSON, nullable=False)  # Can be int, bool, or array of ints
    order = Column(Integer, nullable=False)  # Display order within quiz
    explanation = Column(Text, nullable=True)  # Explanation shown after answering
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class UserQuizAttempt(Base):
    __tablename__ = "user_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)  # Number of correct answers
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Integer, nullable=False)  # Score percentage
    answers = Column(JSON, nullable=False)  # Map of question_id -> user_answer
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="quiz_attempts")
    quiz = relationship("Quiz", back_populates="user_attempts")

    # Index for quick lookups of user's quiz history
    __table_args__ = (
        UniqueConstraint('user_id', 'quiz_id', 'completed_at', name='uq_user_quiz_attempt_time'),
    )

