"""Lớp học, nhóm thực nghiệm / đối chứng, giao bài cho lớp (FR-W02, FR-W12)."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from tutor_backend.core.errors import ForbiddenError, InvalidError, NotFoundError
from tutor_backend.models import Class, ClassExercise, ClassMember, Exercise, User
from tutor_backend.models.enums import Role
from tutor_backend.schemas.class_ import ClassCreate, ClassExerciseIn, ClassOut, MemberIn


def _to_out(db: Session, cls: Class) -> ClassOut:
    count = db.scalar(select(func.count()).where(ClassMember.class_id == cls.id)) or 0
    return ClassOut.model_validate(cls).model_copy(update={"member_count": count})


def get_class(db: Session, class_id: uuid.UUID) -> Class:
    cls = db.get(Class, class_id)
    if cls is None:
        raise NotFoundError("Không tìm thấy lớp", code="class_not_found")
    return cls


def ensure_can_manage(cls: Class, user: User) -> None:
    """Quản trị quản lý mọi lớp; giảng viên chỉ lớp mình phụ trách."""
    if user.role != Role.ADMIN and cls.teacher_id != user.id:
        raise ForbiddenError("Bạn không phụ trách lớp này", code="not_class_teacher")


def list_classes(db: Session, user: User) -> list[ClassOut]:
    query = select(Class).order_by(Class.name)
    if user.role != Role.ADMIN:
        query = query.where(Class.teacher_id == user.id)
    return [_to_out(db, cls) for cls in db.scalars(query)]


def create_class(db: Session, data: ClassCreate) -> ClassOut:
    teacher = db.get(User, data.teacher_id)
    if teacher is None or teacher.role != Role.TEACHER:
        raise InvalidError("teacher_id phải là tài khoản giảng viên", code="not_a_teacher")
    cls = Class(**data.model_dump())
    db.add(cls)
    db.commit()
    return _to_out(db, cls)


def replace_members(db: Session, class_id: uuid.UUID, members: list[MemberIn]) -> None:
    """Thay toàn bộ danh sách học viên của lớp (PUT): người nào không có trong danh sách bị gỡ khỏi lớp."""
    get_class(db, class_id)
    ids = [m.student_id for m in members]
    if len(ids) != len(set(ids)):
        raise InvalidError("Một học viên xuất hiện hai lần", code="duplicate_member")
    students = {u.id for u in db.scalars(select(User).where(User.id.in_(ids), User.role == Role.STUDENT))}
    missing = [str(i) for i in ids if i not in students]
    if missing:
        errors = [{"path": "/student_id", "message": f"{i} không phải học viên"} for i in missing]
        raise InvalidError("Danh sách có tài khoản không phải học viên", code="not_a_student", errors=errors)
    db.execute(delete(ClassMember).where(ClassMember.class_id == class_id))
    db.add_all(
        ClassMember(class_id=class_id, student_id=m.student_id, study_group=m.study_group) for m in members
    )
    db.commit()


def assign_exercise(db: Session, class_id: uuid.UUID, data: ClassExerciseIn, user: User) -> None:
    cls = get_class(db, class_id)
    ensure_can_manage(cls, user)
    if db.get(Exercise, data.exercise_id) is None:
        raise NotFoundError("Không tìm thấy bài tập", code="exercise_not_found")
    existing = db.get(ClassExercise, (class_id, data.exercise_id))
    if existing is None:
        db.add(ClassExercise(class_id=class_id, exercise_id=data.exercise_id, due_at=data.due_at))
    else:
        existing.due_at = data.due_at
    db.commit()
