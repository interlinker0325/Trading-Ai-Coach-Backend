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
    PracticeSession,
    PracticeTrade,
    Playbook,
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
    PracticeSessionCreate,
    PracticeSessionUpdate,
    PracticeTradeCreate,
    PracticeTradeUpdate,
    TradeExecutionRequest,
    PlaybookCreate,
    PlaybookUpdate,
)
from datetime import datetime
from app.models.education import PracticeSessionStatus, TradeStatus, TradeType


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


# Practice Session CRUD
def get_practice_session(db: Session, session_id: int, user_id: Optional[int] = None) -> Optional[PracticeSession]:
    """Get practice session by ID, optionally filtered by user"""
    query = db.query(PracticeSession).filter(PracticeSession.id == session_id)
    if user_id:
        query = query.filter(PracticeSession.user_id == user_id)
    return query.first()


def get_practice_sessions(
    db: Session,
    user_id: int,
    status: Optional[PracticeSessionStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[PracticeSession]:
    """Get user's practice sessions with optional filtering"""
    query = db.query(PracticeSession).filter(PracticeSession.user_id == user_id)
    
    if status:
        query = query.filter(PracticeSession.status == status)
    
    return query.order_by(PracticeSession.created_at.desc()).offset(skip).limit(limit).all()


def create_practice_session(db: Session, session: PracticeSessionCreate, user_id: int) -> PracticeSession:
    """Create a new practice session"""
    db_session = PracticeSession(
        user_id=user_id,
        playbook_id=session.playbook_id,
        playbook_data=session.playbook_data,
        symbol=session.symbol,
        initial_balance=session.initial_balance or 100000.0,
        current_balance=session.initial_balance or 100000.0,
        status=PracticeSessionStatus.ACTIVE,
        current_step=1,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def update_practice_session(
    db: Session,
    session_id: int,
    session_update: PracticeSessionUpdate,
    user_id: Optional[int] = None,
) -> Optional[PracticeSession]:
    """Update practice session"""
    query = db.query(PracticeSession).filter(PracticeSession.id == session_id)
    if user_id:
        query = query.filter(PracticeSession.user_id == user_id)
    
    db_session = query.first()
    if not db_session:
        return None
    
    update_data = session_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)
    
    # If completing session, set completed_at
    if update_data.get("status") == PracticeSessionStatus.COMPLETED and not db_session.completed_at:
        db_session.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_session)
    return db_session


def delete_practice_session(db: Session, session_id: int, user_id: Optional[int] = None) -> bool:
    """Delete practice session (or mark as abandoned)"""
    query = db.query(PracticeSession).filter(PracticeSession.id == session_id)
    if user_id:
        query = query.filter(PracticeSession.user_id == user_id)
    
    db_session = query.first()
    if not db_session:
        return False
    
    # Mark as abandoned instead of deleting
    db_session.status = PracticeSessionStatus.ABANDONED
    db.commit()
    return True


def advance_practice_step(db: Session, session_id: int, user_id: int) -> Optional[PracticeSession]:
    """Advance to next step in practice session"""
    db_session = get_practice_session(db, session_id, user_id)
    if not db_session or db_session.status != PracticeSessionStatus.ACTIVE:
        return None
    
    # Get playbook data to determine total steps
    playbook_data = db_session.playbook_data or {}
    steps = playbook_data.get("steps", [])
    total_steps = len(steps)
    
    if db_session.current_step < total_steps:
        db_session.current_step += 1
    else:
        # Completed all steps
        db_session.status = PracticeSessionStatus.COMPLETED
        db_session.completed_at = datetime.utcnow()
        # Calculate final performance metrics
        db_session.performance_metrics = calculate_performance_metrics(db, db_session)
    
    db.commit()
    db.refresh(db_session)
    return db_session


def calculate_performance_metrics(db: Session, session: PracticeSession) -> dict:
    """Calculate performance metrics for a session"""
    trades = db.query(PracticeTrade).filter(
        PracticeTrade.session_id == session.id,
        PracticeTrade.status == TradeStatus.CLOSED,
    ).all()
    
    if not trades:
        return {
            "total_pnl": 0.0,
            "total_pnl_percentage": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
        }
    
    total_pnl = sum(trade.pnl or 0.0 for trade in trades)
    total_pnl_percentage = ((session.current_balance - session.initial_balance) / session.initial_balance) * 100
    
    winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl and t.pnl < 0]
    
    win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
    
    average_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else None
    average_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else None
    
    # Calculate max drawdown
    balance_history = [session.initial_balance]
    for trade in sorted(trades, key=lambda x: x.created_at):
        if trade.pnl:
            balance_history.append(balance_history[-1] + trade.pnl)
    
    if len(balance_history) > 1:
        peak = balance_history[0]
        max_drawdown = 0.0
        for balance in balance_history:
            if balance > peak:
                peak = balance
            drawdown = ((peak - balance) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    else:
        max_drawdown = None
    
    return {
        "total_pnl": total_pnl,
        "total_pnl_percentage": total_pnl_percentage,
        "win_rate": win_rate,
        "total_trades": len(trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "average_win": average_win,
        "average_loss": average_loss,
        "max_drawdown": max_drawdown,
    }


# Practice Trade CRUD
def get_practice_trade(db: Session, trade_id: int) -> Optional[PracticeTrade]:
    """Get practice trade by ID"""
    return db.query(PracticeTrade).filter(PracticeTrade.id == trade_id).first()


def get_practice_trades(
    db: Session,
    session_id: int,
    status: Optional[TradeStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[PracticeTrade]:
    """Get trades for a practice session"""
    query = db.query(PracticeTrade).filter(PracticeTrade.session_id == session_id)
    
    if status:
        query = query.filter(PracticeTrade.status == status)
    
    return query.order_by(PracticeTrade.created_at.desc()).offset(skip).limit(limit).all()


def execute_trade(
    db: Session,
    session_id: int,
    trade_request: TradeExecutionRequest,
    current_price: float,
) -> PracticeTrade:
    """Execute a trade in a practice session"""
    session = get_practice_session(db, session_id)
    if not session or session.status != PracticeSessionStatus.ACTIVE:
        raise ValueError("Session not found or not active")
    
    # Use current_price if entry_price not provided (market order)
    entry_price = trade_request.entry_price or current_price
    
    # Calculate cost
    cost = entry_price * trade_request.quantity
    
    # Check if user has enough balance for buy orders
    if trade_request.trade_type == TradeType.BUY:
        if session.current_balance < cost:
            raise ValueError("Insufficient balance")
        session.current_balance -= cost
    elif trade_request.trade_type == TradeType.SELL:
        # For sell orders, we need to check if user has open positions
        # Simplified: just add to balance
        session.current_balance += cost
    
    # Create trade
    db_trade = PracticeTrade(
        session_id=session_id,
        step_number=session.current_step,
        trade_type=trade_request.trade_type,
        symbol=trade_request.symbol,
        quantity=trade_request.quantity,
        entry_price=entry_price,
        stop_loss=trade_request.stop_loss,
        take_profit=trade_request.take_profit,
        status=TradeStatus.OPEN,
    )
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade


def close_trade(
    db: Session,
    trade_id: int,
    exit_price: float,
    user_id: Optional[int] = None,
) -> Optional[PracticeTrade]:
    """Close a trade"""
    db_trade = get_practice_trade(db, trade_id)
    if not db_trade or db_trade.status != TradeStatus.OPEN:
        return None
    
    # Verify session ownership if user_id provided
    if user_id:
        session = get_practice_session(db, db_trade.session_id, user_id)
        if not session:
            return None
    
    # Calculate P&L
    if db_trade.trade_type == TradeType.BUY:
        pnl = (exit_price - db_trade.entry_price) * db_trade.quantity
    else:  # SELL
        pnl = (db_trade.entry_price - exit_price) * db_trade.quantity
    
    pnl_percentage = ((exit_price - db_trade.entry_price) / db_trade.entry_price) * 100
    
    # Update trade
    db_trade.exit_price = exit_price
    db_trade.pnl = pnl
    db_trade.pnl_percentage = pnl_percentage
    db_trade.status = TradeStatus.CLOSED
    db_trade.closed_at = datetime.utcnow()
    
    # Update session balance
    session = get_practice_session(db, db_trade.session_id)
    if session:
        session.current_balance += pnl
    
    db.commit()
    db.refresh(db_trade)
    return db_trade


def update_trade(
    db: Session,
    trade_id: int,
    trade_update: PracticeTradeUpdate,
) -> Optional[PracticeTrade]:
    """Update trade (e.g., modify stop loss/take profit)"""
    db_trade = get_practice_trade(db, trade_id)
    if not db_trade:
        return None
    
    update_data = trade_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trade, field, value)
    
    db.commit()
    db.refresh(db_trade)
    return db_trade


# Playbook CRUD
def get_playbook(db: Session, playbook_id: int) -> Optional[Playbook]:
    """Get playbook by ID"""
    return db.query(Playbook).filter(Playbook.id == playbook_id).first()


def get_playbooks(
    db: Session,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Playbook]:
    """Get all playbooks with optional filtering"""
    query = db.query(Playbook)

    if category:
        query = query.filter(Playbook.category.ilike(f"%{category}%"))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Playbook.title.ilike(search_term))
            | (Playbook.description.ilike(search_term))
        )

    return query.order_by(Playbook.created_at.desc()).offset(skip).limit(limit).all()


def create_playbook(db: Session, playbook: PlaybookCreate) -> Playbook:
    """Create a new playbook"""
    # Convert steps to JSON format
    steps_json = [step.model_dump() for step in playbook.steps]
    
    db_playbook = Playbook(
        title=playbook.title,
        description=playbook.description,
        category=playbook.category,
        level=playbook.level,
        icon=playbook.icon,
        steps=steps_json,
    )
    db.add(db_playbook)
    db.commit()
    db.refresh(db_playbook)
    return db_playbook


def update_playbook(
    db: Session, playbook_id: int, playbook_update: PlaybookUpdate
) -> Optional[Playbook]:
    """Update playbook"""
    db_playbook = get_playbook(db, playbook_id)
    if not db_playbook:
        return None

    update_data = playbook_update.model_dump(exclude_unset=True)
    
    # Convert steps to JSON if provided
    if "steps" in update_data and update_data["steps"] is not None:
        update_data["steps"] = [step.model_dump() for step in update_data["steps"]]
    
    for field, value in update_data.items():
        setattr(db_playbook, field, value)

    db.commit()
    db.refresh(db_playbook)
    return db_playbook


def delete_playbook(db: Session, playbook_id: int) -> bool:
    """Delete playbook"""
    db_playbook = get_playbook(db, playbook_id)
    if not db_playbook:
        return False

    db.delete(db_playbook)
    db.commit()
    return True
