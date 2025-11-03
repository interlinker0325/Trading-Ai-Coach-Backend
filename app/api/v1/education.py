from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.security import verify_token
from app.crud.user import get_user_by_id
from app.crud.education import (
    get_courses,
    get_course,
    create_course,
    update_course,
    delete_course,
    get_lesson,
    get_lessons_by_course,
    mark_lesson_complete,
    get_user_course_progress,
    get_user_lesson_progress,
    get_quizzes,
    get_quiz,
    create_quiz,
    update_quiz,
    delete_quiz,
    submit_quiz_answers,
    get_user_quiz_attempts,
    get_user_best_quiz_score,
    get_user_quiz_attempts_count,
)
from app.schemas.education import (
    CourseResponse,
    CourseCreate,
    CourseUpdate,
    LessonResponse,
    CourseProgressResponse,
    QuizResponse,
    QuizCreate,
    QuizUpdate,
    QuizSubmission,
    QuizResult,
    QuizAttemptHistory,
)

security = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        token_data = verify_token(token, "access")
        if token_data is None:
            return None
        
        user_id = token_data.get("sub")
        if user_id is None:
            return None
        
        user = get_user_by_id(db, user_id=int(user_id))
        return user
    except Exception:
        return None


router = APIRouter()


# Courses endpoints
@router.get("/courses", response_model=List[CourseResponse])
def list_courses(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title, description, instructor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get all courses with optional filtering"""
    courses = get_courses(db, category=category, search=search, skip=skip, limit=limit)
    
    result = []
    for course in courses:
        course_dict = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level.value,
            "duration": course.duration,
            "modules": course.modules,
            "category": course.category,
            "instructor": course.instructor,
            "icon": course.icon,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "progress": 0,
            "lessons": [],
        }

        # Get lessons
        lessons = get_lessons_by_course(db, course.id)
        lesson_list = []
        completed_count = 0

        for lesson in lessons:
            lesson_dict = {
                "id": lesson.id,
                "course_id": lesson.course_id,
                "title": lesson.title,
                "duration": lesson.duration,
                "type": lesson.type.value,
                "content": lesson.content,
                "order": lesson.order,
                "completed": False,
                "created_at": lesson.created_at,
                "updated_at": lesson.updated_at,
            }

            # Check user's progress if logged in
            if current_user:
                progress = get_user_lesson_progress(db, current_user.id, lesson.id)
                if progress and progress.completed:
                    lesson_dict["completed"] = True
                    completed_count += 1

            lesson_list.append(lesson_dict)

        # Calculate course progress
        if current_user:
            course_progress = get_user_course_progress(db, current_user.id, course.id)
            if course_progress:
                course_dict["progress"] = course_progress.progress
            elif len(lesson_list) > 0:
                course_dict["progress"] = int((completed_count / len(lesson_list)) * 100)

        course_dict["lessons"] = sorted(lesson_list, key=lambda x: x["order"])
        result.append(course_dict)

    return result


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get course details with lessons"""
    course = get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    course_dict = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "level": course.level.value,
        "duration": course.duration,
        "modules": course.modules,
        "category": course.category,
        "instructor": course.instructor,
        "icon": course.icon,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
        "progress": 0,
        "lessons": [],
    }

    # Get lessons
    lessons = get_lessons_by_course(db, course_id)
    lesson_list = []
    completed_count = 0

    for lesson in lessons:
        lesson_dict = {
            "id": lesson.id,
            "course_id": lesson.course_id,
            "title": lesson.title,
            "duration": lesson.duration,
            "type": lesson.type.value,
            "content": lesson.content,
            "order": lesson.order,
            "completed": False,
            "created_at": lesson.created_at,
            "updated_at": lesson.updated_at,
        }

        # Check user's progress if logged in
        if current_user:
            progress = get_user_lesson_progress(db, current_user.id, lesson.id)
            if progress and progress.completed:
                lesson_dict["completed"] = True
                completed_count += 1

        lesson_list.append(lesson_dict)

    # Calculate course progress
    if current_user:
        course_progress = get_user_course_progress(db, current_user.id, course_id)
        if course_progress:
            course_dict["progress"] = course_progress.progress
        elif len(lesson_list) > 0:
            course_dict["progress"] = int((completed_count / len(lesson_list)) * 100)

    course_dict["lessons"] = sorted(lesson_list, key=lambda x: x["order"])
    return course_dict


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_new_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new course (admin only - implement admin check as needed)"""
    created = create_course(db, course)
    return created


@router.put("/courses/{course_id}", response_model=CourseResponse)
def update_course_info(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update course (admin only)"""
    course = update_course(db, course_id, course_update)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete course (admin only)"""
    if not delete_course(db, course_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    return None


# Lessons endpoints
@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def get_lesson_detail(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get lesson details"""
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    lesson_dict = {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "duration": lesson.duration,
        "type": lesson.type.value,
        "content": lesson.content,
        "order": lesson.order,
        "completed": False,
        "created_at": lesson.created_at,
        "updated_at": lesson.updated_at,
    }

    if current_user:
        progress = get_user_lesson_progress(db, current_user.id, lesson_id)
        if progress and progress.completed:
            lesson_dict["completed"] = True

    return lesson_dict


# Progress endpoints
@router.post("/lessons/{lesson_id}/complete", status_code=status.HTTP_200_OK)
def mark_lesson_completed(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a lesson as completed"""
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    progress = mark_lesson_complete(db, current_user.id, lesson_id, completed=True)
    return {"message": "Lesson marked as complete", "lesson_id": lesson_id}


@router.delete("/lessons/{lesson_id}/complete", status_code=status.HTTP_200_OK)
def mark_lesson_incomplete(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a lesson as incomplete"""
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    progress = mark_lesson_complete(db, current_user.id, lesson_id, completed=False)
    return {"message": "Lesson marked as incomplete", "lesson_id": lesson_id}


@router.get("/courses/{course_id}/progress", response_model=CourseProgressResponse)
def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's progress for a specific course"""
    course = get_course(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    progress = get_user_course_progress(db, current_user.id, course_id)
    lessons = get_lessons_by_course(db, course_id)
    completed = sum(
        1
        for lesson in lessons
        if get_user_lesson_progress(db, current_user.id, lesson.id)
        and get_user_lesson_progress(db, current_user.id, lesson.id).completed
    )

    progress_percentage = progress.progress if progress else 0

    return {
        "course_id": course_id,
        "progress": progress_percentage,
        "completed_lessons": completed,
        "total_lessons": len(lessons),
    }


# Quiz endpoints
@router.get("/quizzes", response_model=List[QuizResponse])
def list_quizzes(
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get all quizzes with optional filtering"""
    quizzes = get_quizzes(db, category=category, skip=skip, limit=limit)
    
    result = []
    for quiz in quizzes:
        quiz_dict = {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "category": quiz.category,
            "created_at": quiz.created_at,
            "updated_at": quiz.updated_at,
            "questions": [],
            "best_score": None,
            "attempts_count": 0,
        }

        # Get questions
        question_list = []
        for question in quiz.questions:
            question_dict = {
                "id": question.id,
                "quiz_id": question.quiz_id,
                "question": question.question,
                "question_type": question.question_type.value,
                "options": question.options or [],
                "order": question.order,
                "explanation": question.explanation,
                "created_at": question.created_at,
            }
            question_list.append(question_dict)

        quiz_dict["questions"] = sorted(question_list, key=lambda x: x["order"])

        # Get user's best score and attempts count if authenticated
        if current_user:
            best_score = get_user_best_quiz_score(db, current_user.id, quiz.id)
            attempts_count = get_user_quiz_attempts_count(db, current_user.id, quiz.id)
            quiz_dict["best_score"] = best_score
            quiz_dict["attempts_count"] = attempts_count

        result.append(quiz_dict)

    return result


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
def get_quiz_detail(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get quiz details with questions"""
    quiz = get_quiz(db, quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found"
        )

    quiz_dict = {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "category": quiz.category,
        "created_at": quiz.created_at,
        "updated_at": quiz.updated_at,
        "questions": [],
        "best_score": None,
        "attempts_count": 0,
    }

    # Get questions (don't include correct_answer - that's hidden until submission)
    question_list = []
    for question in quiz.questions:
        question_dict = {
            "id": question.id,
            "quiz_id": question.quiz_id,
            "question": question.question,
            "question_type": question.question_type.value,
            "options": question.options or [],
            "order": question.order,
            "explanation": question.explanation,
            "created_at": question.created_at,
        }
        question_list.append(question_dict)

    quiz_dict["questions"] = sorted(question_list, key=lambda x: x["order"])

    # Get user's best score and attempts count if authenticated
    if current_user:
        best_score = get_user_best_quiz_score(db, current_user.id, quiz_id)
        attempts_count = get_user_quiz_attempts_count(db, current_user.id, quiz_id)
        quiz_dict["best_score"] = best_score
        quiz_dict["attempts_count"] = attempts_count

    return quiz_dict


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResult, status_code=status.HTTP_200_OK)
def submit_quiz(
    quiz_id: int,
    submission: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit quiz answers and get results"""
    try:
        attempt = submit_quiz_answers(db, current_user.id, quiz_id, submission)
        
        # Get the quiz to calculate question results
        quiz = get_quiz(db, quiz_id)
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found"
            )

        # Calculate question results for response and collect correct answers
        question_results = {}
        correct_answers = {}
        for question in quiz.questions:
            user_answer = submission.answers.get(question.id)
            if user_answer is None:
                question_results[question.id] = False
                correct_answers[question.id] = question.correct_answer
                continue

            is_correct = False
            if question.question_type.value == "multiple-choice":
                is_correct = user_answer == question.correct_answer
            elif question.question_type.value == "true-false":
                is_correct = user_answer == question.correct_answer
            elif question.question_type.value == "multiple-select":
                if isinstance(user_answer, list) and isinstance(question.correct_answer, list):
                    is_correct = sorted(user_answer) == sorted(question.correct_answer)
            
            question_results[question.id] = is_correct
            correct_answers[question.id] = question.correct_answer

        return QuizResult(
            quiz_id=quiz_id,
            score=attempt.score,
            total_questions=attempt.total_questions,
            percentage=attempt.percentage,
            answers=submission.answers,
            question_results=question_results,
            correct_answers=correct_answers,
            completed_at=attempt.completed_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.get("/quizzes/{quiz_id}/attempts", response_model=List[QuizAttemptHistory])
def get_quiz_attempts(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's attempts for a specific quiz"""
    quiz = get_quiz(db, quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found"
        )

    attempts = get_user_quiz_attempts(db, current_user.id, quiz_id)
    
    return [
        QuizAttemptHistory(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            quiz_title=quiz.title,
            score=attempt.score,
            total_questions=attempt.total_questions,
            percentage=attempt.percentage,
            completed_at=attempt.completed_at,
        )
        for attempt in attempts
    ]


@router.get("/quizzes/history/all", response_model=List[QuizAttemptHistory])
def get_all_quiz_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's all quiz attempts"""
    attempts = get_user_quiz_attempts(db, current_user.id)
    
    # Get quiz titles for each attempt
    result = []
    for attempt in attempts:
        quiz = get_quiz(db, attempt.quiz_id)
        if quiz:
            result.append(
                QuizAttemptHistory(
                    id=attempt.id,
                    quiz_id=attempt.quiz_id,
                    quiz_title=quiz.title,
                    score=attempt.score,
                    total_questions=attempt.total_questions,
                    percentage=attempt.percentage,
                    completed_at=attempt.completed_at,
                )
            )
    
    return result


@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
def create_new_quiz(
    quiz: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new quiz (admin only - implement admin check as needed)"""
    created = create_quiz(db, quiz)
    return created


@router.put("/quizzes/{quiz_id}", response_model=QuizResponse)
def update_quiz_info(
    quiz_id: int,
    quiz_update: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update quiz (admin only)"""
    quiz = update_quiz(db, quiz_id, quiz_update)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found"
        )
    return quiz


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz_endpoint(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete quiz (admin only)"""
    if not delete_quiz(db, quiz_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found"
        )
    return None
