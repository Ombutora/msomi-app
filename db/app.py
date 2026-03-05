"""
app.py  –  Msomi App  (single-file Flask backend)
Run:   python app.py
Seed:  python seed.py
"""

import os, json
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash

# ── App & config ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"]                  = os.environ.get("SECRET_KEY", "msomi-dev-secret")
app.config["JWT_SECRET_KEY"]              = os.environ.get("JWT_SECRET_KEY", "msomi-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"]    = timedelta(hours=8)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"]     = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'msomi.db')}"
)

db  = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Group(db.Model):
    __tablename__ = "groups"
    id   = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128))

    members      = db.relationship("User",         back_populates="group",   lazy="dynamic")
    class_slots  = db.relationship("ClassSlot",    back_populates="group",   lazy="dynamic")
    announcements = db.relationship("Announcement", back_populates="group",  lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name}


class Lecturer(db.Model):
    __tablename__ = "lecturers"
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(128), nullable=False)
    shortcode = db.Column(db.String(16))

    user        = db.relationship("User",      back_populates="lecturer", uselist=False)
    class_slots = db.relationship("ClassSlot", back_populates="lecturer", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "shortcode": self.shortcode}


class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(16),  nullable=False)   # student|teacher|rep
    full_name     = db.Column(db.String(128), nullable=False)
    group_id      = db.Column(db.Integer, db.ForeignKey("groups.id"),    nullable=True)
    lecturer_id   = db.Column(db.Integer, db.ForeignKey("lecturers.id"), nullable=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    group    = db.relationship("Group",    back_populates="members")
    lecturer = db.relationship("Lecturer", back_populates="user", foreign_keys=[lecturer_id])

    reviews_given    = db.relationship("Review", foreign_keys="Review.from_user_id", back_populates="from_user",  lazy="dynamic")
    reviews_received = db.relationship("Review", foreign_keys="Review.to_user_id",   back_populates="to_user",    lazy="dynamic")
    notifications    = db.relationship("Notification", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        d = {"id": self.id, "username": self.username, "role": self.role, "full_name": self.full_name}
        if self.group:
            d["group"] = self.group.to_dict()
        if self.lecturer_id:
            d["lecturer_id"] = self.lecturer_id
        return d


class Course(db.Model):
    __tablename__ = "courses"
    id   = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16),  unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)

    class_slots = db.relationship("ClassSlot", back_populates="course",   lazy="dynamic")
    resources   = db.relationship("Resource",  back_populates="course",   lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name}


class ClassSlot(db.Model):
    __tablename__ = "class_slots"
    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"),   nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.id"), nullable=False)
    group_id    = db.Column(db.Integer, db.ForeignKey("groups.id"),    nullable=False)
    day         = db.Column(db.String(16), nullable=False)
    start_time  = db.Column(db.String(8),  nullable=False)
    end_time    = db.Column(db.String(8),  nullable=False)
    venue       = db.Column(db.String(64), nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    course   = db.relationship("Course",   back_populates="class_slots")
    lecturer = db.relationship("Lecturer", back_populates="class_slots")
    group    = db.relationship("Group",    back_populates="class_slots")
    reviews  = db.relationship("Review",   back_populates="class_slot", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, full=False):
        d = {
            "id": self.id, "day": self.day,
            "start_time": self.start_time, "end_time": self.end_time,
            "venue": self.venue, "course_id": self.course_id,
            "lecturer_id": self.lecturer_id, "group_id": self.group_id,
        }
        if full:
            d["course"]   = self.course.to_dict()   if self.course   else None
            d["lecturer"] = self.lecturer.to_dict() if self.lecturer else None
            d["group"]    = self.group.to_dict()    if self.group    else None
        return d


class Review(db.Model):
    __tablename__ = "reviews"
    id             = db.Column(db.Integer, primary_key=True)
    class_id       = db.Column(db.Integer, db.ForeignKey("class_slots.id"), nullable=False)
    from_user_id   = db.Column(db.Integer, db.ForeignKey("users.id"),       nullable=False)
    to_user_id     = db.Column(db.Integer, db.ForeignKey("users.id"),       nullable=True)
    to_lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.id"),   nullable=True)
    rating         = db.Column(db.Integer, nullable=False)
    comment        = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    class_slot  = db.relationship("ClassSlot", back_populates="reviews")
    from_user   = db.relationship("User",     foreign_keys=[from_user_id], back_populates="reviews_given")
    to_user     = db.relationship("User",     foreign_keys=[to_user_id],   back_populates="reviews_received")
    to_lecturer = db.relationship("Lecturer", foreign_keys=[to_lecturer_id])

    def to_dict(self):
        d = {
            "id": self.id, "class_id": self.class_id,
            "from_user_id": self.from_user_id,
            "from_name": self.from_user.full_name if self.from_user else "",
            "rating": self.rating, "comment": self.comment,
            "created_at": self.created_at.isoformat(),
        }
        if self.to_user:
            d["to_user_id"] = self.to_user_id
            d["to_name"]    = self.to_user.full_name
        if self.to_lecturer_id:
            d["to_lecturer_id"] = self.to_lecturer_id
            d["to_name"]        = self.to_lecturer.name if self.to_lecturer else ""
        return d


class Notification(db.Model):
    __tablename__ = "notifications"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type       = db.Column(db.String(32), default="reminder")
    text       = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {"id": self.id, "type": self.type, "text": self.text,
                "is_read": self.is_read, "created_at": self.created_at.isoformat()}


class Announcement(db.Model):
    __tablename__ = "announcements"
    id         = db.Column(db.Integer, primary_key=True)
    group_id   = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    posted_by  = db.Column(db.Integer, db.ForeignKey("users.id"),  nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    body       = db.Column(db.Text,        nullable=False)
    type       = db.Column(db.String(32),  default="general")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    group  = db.relationship("Group", back_populates="announcements")
    author = db.relationship("User",  foreign_keys=[posted_by])

    def to_dict(self):
        return {"id": self.id, "group_id": self.group_id, "posted_by": self.posted_by,
                "author": self.author.full_name if self.author else "",
                "title": self.title, "body": self.body, "type": self.type,
                "created_at": self.created_at.isoformat()}


class Resource(db.Model):
    __tablename__ = "resources"
    id         = db.Column(db.Integer, primary_key=True)
    course_id  = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    added_by   = db.Column(db.Integer, db.ForeignKey("users.id"),   nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    link       = db.Column(db.Text,        nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    course   = db.relationship("Course", back_populates="resources")
    uploader = db.relationship("User",   foreign_keys=[added_by])

    def to_dict(self):
        return {"id": self.id, "course_id": self.course_id,
                "course": self.course.to_dict() if self.course else None,
                "added_by": self.added_by,
                "added_by_name": self.uploader.full_name if self.uploader else "",
                "title": self.title, "link": self.link,
                "created_at": self.created_at.isoformat()}


class UserSettings(db.Model):
    __tablename__ = "user_settings"
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    data_json = db.Column(db.Text, default="{}")

    @property
    def data(self):
        return json.loads(self.data_json or "{}")

    @data.setter
    def data(self, val):
        self.data_json = json.dumps(val)


# ── Create tables ─────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def current_user():
    return User.query.get(int(get_jwt_identity()))


_SETTINGS_DEFAULTS = {"leadTime": 30, "toast": True, "sound": False}

def get_or_create_settings(user_id):
    s = UserSettings.query.get(user_id)
    if not s:
        s = UserSettings(user_id=user_id)
        s.data = _SETTINGS_DEFAULTS.copy()
        db.session.add(s)
        db.session.commit()
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Health
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Auth
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/login")
def login():
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    if role and user.role != role:
        return jsonify({"error": "Role mismatch"}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), 200


@app.get("/api/auth/me")
@jwt_required()
def me():
    return jsonify(current_user().to_dict()), 200


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Reference data  (courses, lecturers, groups)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/courses")
@jwt_required()
def list_courses():
    return jsonify([c.to_dict() for c in Course.query.order_by(Course.code).all()])


@app.get("/api/lecturers")
@jwt_required()
def list_lecturers():
    return jsonify([l.to_dict() for l in Lecturer.query.order_by(Lecturer.name).all()])


@app.get("/api/groups")
@jwt_required()
def list_groups():
    return jsonify([g.to_dict() for g in Group.query.order_by(Group.code).all()])


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Classes (timetable)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/classes")
@jwt_required()
def list_classes():
    me = current_user()
    q  = ClassSlot.query

    group_id    = request.args.get("group_id",    type=int)
    lecturer_id = request.args.get("lecturer_id", type=int)
    day         = request.args.get("day")

    if group_id:    q = q.filter_by(group_id=group_id)
    if lecturer_id: q = q.filter_by(lecturer_id=lecturer_id)
    if day:         q = q.filter_by(day=day)

    # Auto-scope by role if no explicit filter given
    if me.role in ("student", "rep") and not group_id:
        q = q.filter_by(group_id=me.group_id)
    elif me.role == "teacher" and not lecturer_id and me.lecturer_id:
        q = q.filter_by(lecturer_id=me.lecturer_id)

    return jsonify([c.to_dict(full=True) for c in q.order_by(ClassSlot.day, ClassSlot.start_time).all()])


@app.post("/api/classes")
@jwt_required()
def create_class():
    me = current_user()
    if me.role != "rep":
        return jsonify({"error": "Only class reps can create classes"}), 403

    data        = request.get_json(silent=True) or {}
    course_id   = data.get("course_id")
    lecturer_id = data.get("lecturer_id")
    day         = data.get("day")
    start_time  = data.get("start_time")
    end_time    = data.get("end_time")
    venue       = (data.get("venue") or "").strip()

    if not all([course_id, lecturer_id, day, start_time, end_time, venue]):
        return jsonify({"error": "All fields are required"}), 400
    if not Course.query.get(course_id):
        return jsonify({"error": "Course not found"}), 404
    if not Lecturer.query.get(lecturer_id):
        return jsonify({"error": "Lecturer not found"}), 404

    conflict = ClassSlot.query.filter(
        ClassSlot.group_id   == me.group_id,
        ClassSlot.day        == day,
        ClassSlot.start_time <  end_time,
        ClassSlot.end_time   >  start_time,
    ).first()
    if conflict:
        c = Course.query.get(conflict.course_id)
        return jsonify({"error": f"Conflict with {c.code} ({conflict.start_time}–{conflict.end_time})"}), 409

    slot = ClassSlot(course_id=course_id, lecturer_id=lecturer_id, group_id=me.group_id,
                     day=day, start_time=start_time, end_time=end_time, venue=venue)
    db.session.add(slot)
    db.session.commit()
    return jsonify(slot.to_dict(full=True)), 201


@app.put("/api/classes/<int:class_id>")
@jwt_required()
def update_class(class_id):
    me   = current_user()
    if me.role != "rep":
        return jsonify({"error": "Only class reps can edit classes"}), 403

    slot = ClassSlot.query.get_or_404(class_id)
    data = request.get_json(silent=True) or {}

    new_day   = data.get("day",        slot.day)
    new_start = data.get("start_time", slot.start_time)
    new_end   = data.get("end_time",   slot.end_time)

    conflict = ClassSlot.query.filter(
        ClassSlot.id      != class_id,
        ClassSlot.group_id == me.group_id,
        ClassSlot.day      == new_day,
        ClassSlot.start_time < new_end,
        ClassSlot.end_time   > new_start,
    ).first()
    if conflict:
        return jsonify({"error": "Schedule conflict detected"}), 409

    slot.course_id   = data.get("course_id",   slot.course_id)
    slot.lecturer_id = data.get("lecturer_id", slot.lecturer_id)
    slot.day         = new_day
    slot.start_time  = new_start
    slot.end_time    = new_end
    slot.venue       = data.get("venue", slot.venue)
    db.session.commit()
    return jsonify(slot.to_dict(full=True))


@app.delete("/api/classes/<int:class_id>")
@jwt_required()
def delete_class(class_id):
    me = current_user()
    if me.role != "rep":
        return jsonify({"error": "Only class reps can delete classes"}), 403
    slot = ClassSlot.query.get_or_404(class_id)
    db.session.delete(slot)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Reviews
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/reviews")
@jwt_required()
def list_reviews():
    q = Review.query
    if v := request.args.get("class_id",       type=int): q = q.filter_by(class_id=v)
    if v := request.args.get("to_lecturer_id", type=int): q = q.filter_by(to_lecturer_id=v)
    if v := request.args.get("to_user_id",     type=int): q = q.filter_by(to_user_id=v)
    if v := request.args.get("from_user_id",   type=int): q = q.filter_by(from_user_id=v)
    return jsonify([r.to_dict() for r in q.order_by(Review.created_at.desc()).all()])


@app.get("/api/reviews/summary")
@jwt_required()
def reviews_summary():
    from sqlalchemy import func
    group_id = request.args.get("group_id", type=int)
    q = (db.session.query(Review.to_lecturer_id,
                          func.avg(Review.rating).label("avg"),
                          func.count(Review.id).label("cnt"))
         .group_by(Review.to_lecturer_id))
    if group_id:
        ids = [c.id for c in ClassSlot.query.filter_by(group_id=group_id).all()]
        q   = q.filter(Review.class_id.in_(ids))
    result = []
    for row in q.all():
        lec = Lecturer.query.get(row.to_lecturer_id)
        result.append({"lecturer_id": row.to_lecturer_id,
                        "lecturer_name": lec.name if lec else "Unknown",
                        "avg_rating": round(float(row.avg), 2),
                        "count": row.cnt})
    return jsonify(result)


@app.post("/api/reviews")
@jwt_required()
def create_review():
    me   = current_user()
    data = request.get_json(silent=True) or {}
    class_id = data.get("class_id")
    rating   = data.get("rating")
    comment  = data.get("comment", "")

    if not class_id or not rating:
        return jsonify({"error": "class_id and rating required"}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({"error": "Rating must be 1-5"}), 400
    if not ClassSlot.query.get(class_id):
        return jsonify({"error": "Class not found"}), 404

    review = Review(class_id=class_id, from_user_id=me.id,
                    rating=int(rating), comment=comment)

    if me.role == "student":
        slot = ClassSlot.query.get(class_id)
        review.to_lecturer_id = slot.lecturer_id
    else:
        to_uid = data.get("to_user_id")
        if not to_uid:
            return jsonify({"error": "to_user_id required for teacher reviews"}), 400
        review.to_user_id = to_uid

    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201


@app.delete("/api/reviews/<int:review_id>")
@jwt_required()
def delete_review(review_id):
    me     = current_user()
    review = Review.query.get_or_404(review_id)
    if review.from_user_id != me.id:
        return jsonify({"error": "Cannot delete someone else's review"}), 403
    db.session.delete(review)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Notifications
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/notifications")
@jwt_required()
def list_notifications():
    me = current_user()
    notifs = Notification.query.filter_by(user_id=me.id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifs])


@app.post("/api/notifications")
@jwt_required()
def create_notification():
    me   = current_user()
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    n = Notification(user_id=data.get("user_id", me.id),
                     type=data.get("type", "reminder"), text=text)
    db.session.add(n)
    db.session.commit()
    return jsonify(n.to_dict()), 201


@app.patch("/api/notifications/read-all")
@jwt_required()
def mark_all_read():
    me = current_user()
    Notification.query.filter_by(user_id=me.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All marked read"})


@app.patch("/api/notifications/<int:nid>/read")
@jwt_required()
def mark_read(nid):
    me = current_user()
    n  = Notification.query.get_or_404(nid)
    if n.user_id != me.id:
        return jsonify({"error": "Not your notification"}), 403
    n.is_read = True
    db.session.commit()
    return jsonify(n.to_dict())


@app.delete("/api/notifications/<int:nid>")
@jwt_required()
def delete_notification(nid):
    me = current_user()
    n  = Notification.query.get_or_404(nid)
    if n.user_id != me.id:
        return jsonify({"error": "Not your notification"}), 403
    db.session.delete(n)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Announcements
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/announcements")
@jwt_required()
def list_announcements():
    me       = current_user()
    group_id = request.args.get("group_id", type=int) or me.group_id
    q        = Announcement.query
    if group_id:
        q = q.filter_by(group_id=group_id)
    return jsonify([a.to_dict() for a in q.order_by(Announcement.created_at.desc()).all()])


@app.post("/api/announcements")
@jwt_required()
def create_announcement():
    me = current_user()
    if me.role != "rep":
        return jsonify({"error": "Only class reps can post announcements"}), 403
    data  = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    body  = (data.get("body")  or "").strip()
    atype = data.get("type", "general")
    if not title or not body:
        return jsonify({"error": "title and body required"}), 400

    ann = Announcement(group_id=me.group_id, posted_by=me.id,
                       title=title, body=body, type=atype)
    db.session.add(ann)

    # Push notification to all group members
    if me.group:
        for member in me.group.members:
            if member.id != me.id:
                db.session.add(Notification(user_id=member.id, type="announcement",
                                            text=f"{title}: {body[:80]}"))
    db.session.commit()
    return jsonify(ann.to_dict()), 201


@app.delete("/api/announcements/<int:ann_id>")
@jwt_required()
def delete_announcement(ann_id):
    me  = current_user()
    ann = Announcement.query.get_or_404(ann_id)
    if me.role != "rep" or ann.group_id != me.group_id:
        return jsonify({"error": "Not authorised"}), 403
    db.session.delete(ann)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Resources
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/resources")
@jwt_required()
def list_resources():
    q = Resource.query
    if cid := request.args.get("course_id", type=int):
        q = q.filter_by(course_id=cid)
    return jsonify([r.to_dict() for r in q.order_by(Resource.created_at.desc()).all()])


@app.post("/api/resources")
@jwt_required()
def create_resource():
    me = current_user()
    if me.role != "rep":
        return jsonify({"error": "Only class reps can add resources"}), 403
    data      = request.get_json(silent=True) or {}
    title     = (data.get("title") or "").strip()
    course_id = data.get("course_id")
    link      = (data.get("link")  or "").strip()
    if not title or not course_id or not link:
        return jsonify({"error": "title, course_id, and link required"}), 400
    if not Course.query.get(course_id):
        return jsonify({"error": "Course not found"}), 404
    item = Resource(title=title, course_id=course_id, link=link, added_by=me.id)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.delete("/api/resources/<int:resource_id>")
@jwt_required()
def delete_resource(resource_id):
    me   = current_user()
    item = Resource.query.get_or_404(resource_id)
    if me.role != "rep":
        return jsonify({"error": "Only class reps can delete resources"}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES – Settings
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/settings")
@jwt_required()
def get_settings():
    me = current_user()
    s  = get_or_create_settings(me.id)
    return jsonify({**_SETTINGS_DEFAULTS, **s.data})


@app.put("/api/settings")
@jwt_required()
def update_settings():
    me   = current_user()
    s    = get_or_create_settings(me.id)
    data = request.get_json(silent=True) or {}
    s.data = {**_SETTINGS_DEFAULTS, **s.data, **data}
    db.session.commit()
    return jsonify(s.data)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=5000)