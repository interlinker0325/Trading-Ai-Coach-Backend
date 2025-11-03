from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.models.education import (
    Course,
    Lesson,
    UserCourseProgress,
    UserLessonProgress,
    Quiz,
    Question,
    UserQuizAttempt,
)
from app.schemas.education import (
    CourseCreate,
    CourseUpdate,
    LessonCreate,
    LessonUpdate,
    QuizCreate,
    QuizUpdate,
    QuestionCreate,
    QuizSubmission,
)


# Course CRUD
def get_course(db: Session, course_id: int) -> Optional[Course]:
    """Get course by ID"""
    return db.query(Course).filter(Course.id == course_id).first()


def get_courses(
    db: Session,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Course]:
    """Get all courses with optional filtering"""
    query = db.query(Course)

    if category:
        query = query.filter(Course.category.ilike(f"%{category}%"))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Course.title.ilike(search_term))
            | (Course.description.ilike(search_term))
            | (Course.instructor.ilike(search_term))
        )

    return query.offset(skip).limit(limit).all()


def create_course(db: Session, course: CourseCreate) -> Course:
    """Create a new course with lessons"""
    db_course = Course(
        title=course.title,
        description=course.description,
        level=course.level,
        duration=course.duration,
        modules=course.modules,
        category=course.category,
        instructor=course.instructor,
        icon=course.icon,
    )
    db.add(db_course)
    db.flush()  # Get the course ID

    # Create lessons
    for order, lesson_data in enumerate(course.lessons, start=1):
        db_lesson = Lesson(
            course_id=db_course.id,
            title=lesson_data.title,
            duration=lesson_data.duration,
            type=lesson_data.type,
            content=lesson_data.content,
            order=order,
        )
        db.add(db_lesson)

    db.commit()
    db.refresh(db_course)
    return db_course


def update_course(db: Session, course_id: int, course_update: CourseUpdate) -> Optional[Course]:
    """Update course"""
    db_course = get_course(db, course_id)
    if not db_course:
        return None

    update_data = course_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)

    db.commit()
    db.refresh(db_course)
    return db_course


def delete_course(db: Session, course_id: int) -> bool:
    """Delete course"""
    db_course = get_course(db, course_id)
    if not db_course:
        return False
    db.delete(db_course)
    db.commit()
    return True


# Lesson CRUD
def get_lesson(db: Session, lesson_id: int) -> Optional[Lesson]:
    """Get lesson by ID"""
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()


def get_lessons_by_course(db: Session, course_id: int) -> List[Lesson]:
    """Get all lessons for a course"""
    return (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.order)
        .all()
    )


def create_lesson(db: Session, lesson: LessonCreate) -> Lesson:
    """Create a new lesson"""
    db_lesson = Lesson(**lesson.model_dump())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson


def update_lesson(db: Session, lesson_id: int, lesson_update: LessonUpdate) -> Optional[Lesson]:
    """Update lesson"""
    db_lesson = get_lesson(db, lesson_id)
    if not db_lesson:
        return None

    update_data = lesson_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_lesson, field, value)

    db.commit()
    db.refresh(db_lesson)
    return db_lesson


def delete_lesson(db: Session, lesson_id: int) -> bool:
    """Delete lesson"""
    db_lesson = get_lesson(db, lesson_id)
    if not db_lesson:
        return False
    db.delete(db_lesson)
    db.commit()
    return True


# Progress CRUD
def get_user_course_progress(
    db: Session, user_id: int, course_id: int
) -> Optional[UserCourseProgress]:
    """Get user's progress for a specific course"""
    return (
        db.query(UserCourseProgress)
        .filter(
            UserCourseProgress.user_id == user_id,
            UserCourseProgress.course_id == course_id,
        )
        .first()
    )


def get_or_create_user_course_progress(
    db: Session, user_id: int, course_id: int
) -> UserCourseProgress:
    """Get or create user course progress"""
    progress = get_user_course_progress(db, user_id, course_id)
    if not progress:
        progress = UserCourseProgress(user_id=user_id, course_id=course_id, progress=0)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def update_user_course_progress(
    db: Session, user_id: int, course_id: int
) -> UserCourseProgress:
    """Calculate and update user's course progress"""
    progress = get_or_create_user_course_progress(db, user_id, course_id)

    # Count completed lessons
    completed_count = (
        db.query(func.count(UserLessonProgress.id))
        .join(Lesson, UserLessonProgress.lesson_id == Lesson.id)
        .filter(
            UserLessonProgress.user_id == user_id,
            Lesson.course_id == course_id,
            UserLessonProgress.completed == True,
        )
        .scalar()
    )

    # Count total lessons
    total_count = (
        db.query(func.count(Lesson.id)).filter(Lesson.course_id == course_id).scalar()
    )

    # Calculate progress percentage
    if total_count > 0:
        progress.progress = int((completed_count / total_count) * 100)
    else:
        progress.progress = 0

    db.commit()
    db.refresh(progress)
    return progress


def get_user_lesson_progress(
    db: Session, user_id: int, lesson_id: int
) -> Optional[UserLessonProgress]:
    """Get user's progress for a specific lesson"""
    return (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
        .first()
    )


def mark_lesson_complete(
    db: Session, user_id: int, lesson_id: int, completed: bool = True
) -> UserLessonProgress:
    """Mark a lesson as complete or incomplete"""
    progress = get_user_lesson_progress(db, user_id, lesson_id)

    if not progress:
        progress = UserLessonProgress(
            user_id=user_id, lesson_id=lesson_id, completed=completed
        )
        db.add(progress)
    else:
        progress.completed = completed

    if completed:
        from datetime import datetime
        progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)

    # Update course progress
    lesson = get_lesson(db, lesson_id)
    if lesson:
        update_user_course_progress(db, user_id, lesson.course_id)

    return progress


# Quiz CRUD
def get_quiz(db: Session, quiz_id: int) -> Optional[Quiz]:
    """Get quiz by ID"""
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()


def get_quizzes(
    db: Session,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Quiz]:
    """Get all quizzes with optional filtering"""
    query = db.query(Quiz)

    if category:
        query = query.filter(Quiz.category.ilike(f"%{category}%"))

    return query.order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()


def create_quiz(db: Session, quiz: QuizCreate) -> Quiz:
    """Create a new quiz with questions"""
    db_quiz = Quiz(
        title=quiz.title,
        description=quiz.description,
        category=quiz.category,
    )
    db.add(db_quiz)
    db.flush()  # Get the quiz ID

    # Create questions
    for question_data in quiz.questions:
        db_question = Question(
            quiz_id=db_quiz.id,
            question=question_data.question,
            question_type=question_data.question_type,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            order=question_data.order,
            explanation=question_data.explanation,
        )
        db.add(db_question)

    db.commit()
    db.refresh(db_quiz)
    return db_quiz


def update_quiz(db: Session, quiz_id: int, quiz_update: QuizUpdate) -> Optional[Quiz]:
    """Update quiz"""
    db_quiz = get_quiz(db, quiz_id)
    if not db_quiz:
        return None

    update_data = quiz_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_quiz, field, value)

    db.commit()
    db.refresh(db_quiz)
    return db_quiz


def delete_quiz(db: Session, quiz_id: int) -> bool:
    """Delete quiz"""
    db_quiz = get_quiz(db, quiz_id)
    if not db_quiz:
        return False
    db.delete(db_quiz)
    db.commit()
    return True


def submit_quiz_answers(
    db: Session, user_id: int, quiz_id: int, submission: QuizSubmission
) -> UserQuizAttempt:
    """Submit quiz answers and calculate score"""
    quiz = get_quiz(db, quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")

    # Get all questions for this quiz
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).order_by(Question.order).all()

    # Calculate score
    score = 0
    question_results = {}
    
    for question in questions:
        user_answer = submission.answers.get(question.id)
        if user_answer is None:
            question_results[question.id] = False
            continue

        # Check if answer is correct based on question type
        is_correct = False
        if question.question_type.value == "multiple-choice":
            # correct_answer should be an int (index)
            is_correct = user_answer == question.correct_answer
        elif question.question_type.value == "true-false":
            # correct_answer should be a bool
            is_correct = user_answer == question.correct_answer
        elif question.question_type.value == "multiple-select":
            # correct_answer should be a list of ints
            if isinstance(user_answer, list) and isinstance(question.correct_answer, list):
                # Sort both lists for comparison
                user_sorted = sorted(user_answer)
                correct_sorted = sorted(question.correct_answer)
                is_correct = user_sorted == correct_sorted
        
        question_results[question.id] = is_correct
        if is_correct:
            score += 1

    # Calculate percentage
    total_questions = len(questions)
    percentage = int((score / total_questions) * 100) if total_questions > 0 else 0

    # Create attempt record
    attempt = UserQuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        total_questions=total_questions,
        percentage=percentage,
        answers=submission.answers,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def get_user_quiz_attempts(
    db: Session, user_id: int, quiz_id: Optional[int] = None
) -> List[UserQuizAttempt]:
    """Get user's quiz attempts"""
    query = db.query(UserQuizAttempt).filter(UserQuizAttempt.user_id == user_id)
    
    if quiz_id:
        query = query.filter(UserQuizAttempt.quiz_id == quiz_id)
    
    return query.order_by(UserQuizAttempt.completed_at.desc()).all()


def get_user_best_quiz_score(db: Session, user_id: int, quiz_id: int) -> Optional[int]:
    """Get user's best score for a quiz"""
    best = (
        db.query(func.max(UserQuizAttempt.percentage))
        .filter(
            UserQuizAttempt.user_id == user_id,
            UserQuizAttempt.quiz_id == quiz_id,
        )
        .scalar()
    )
    return best


def get_user_quiz_attempts_count(db: Session, user_id: int, quiz_id: int) -> int:
    """Get count of user's attempts for a quiz"""
    return (
        db.query(func.count(UserQuizAttempt.id))
        .filter(
            UserQuizAttempt.user_id == user_id,
            UserQuizAttempt.quiz_id == quiz_id,
        )
        .scalar()
    ) or 0
