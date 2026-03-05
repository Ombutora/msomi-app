"""
seed.py  –  Msomi App database seeder
Usage:  python seed.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from app import (
    Group, Lecturer, User, Course, ClassSlot,
    Review, Notification, Announcement, Resource, UserSettings,
)


def seed():
    with app.app_context():

        # ── Wipe all tables (safe re-seed) ────────────────────────────────
        for model in (Resource, Announcement, Notification,
                      Review, ClassSlot, UserSettings,
                      User, Lecturer, Course, Group):
            db.session.query(model).delete()
        db.session.commit()
        print("✓ Cleared existing data")

        # ── Group ─────────────────────────────────────────────────────────
        g1 = Group(code="CS-Y2S2", name="Computer Science – Year 2 Semester 2")
        db.session.add(g1)
        db.session.flush()
        print(f"✓ Group: {g1.code}")

        # ── Lecturers ─────────────────────────────────────────────────────
        lec_rows = [
            ("l1", "Dr. Lawrence Nderu"),
            ("l2", "Dr. P. Murithi"),
            ("l3", "Dr. Karanja Mwanggi"),
            ("l4", "Dr. Agnes Mindila"),
            ("l5", "Dr. Oteri Omae"),
            ("l6", "Samson Ochinga"),
            ("l7", "Joan Gichuru"),
            ("l8", "Martha Gichuki"),
        ]
        lec_map = {}
        for sc, name in lec_rows:
            lec = Lecturer(name=name, shortcode=sc)
            db.session.add(lec)
            db.session.flush()
            lec_map[sc] = lec
        print(f"✓ {len(lec_rows)} lecturers")

        # ── Courses ───────────────────────────────────────────────────────
        course_rows = [
            ("c1", "ICS2207", "Scientific Computing"),
            ("c2", "ICS2210", "Systems Analysis & Design"),
            ("c3", "ICS2305", "Systems Programming"),
            ("c4", "ICS2218", "Introduction to Quantum Computing"),
            ("c5", "ICS2266", "Digital Electronics"),
            ("c6", "ICS2209", "Computer Networks"),
            ("c7", "ICS2206", "Database Systems"),
            ("c8", "ICS2211", "Numerical Linear Algebra"),
        ]
        course_map = {}
        for old_id, code, name in course_rows:
            c = Course(code=code, name=name)
            db.session.add(c)
            db.session.flush()
            course_map[old_id] = c
        print(f"✓ {len(course_rows)} courses")

        # ── Users ─────────────────────────────────────────────────────────
        user_rows = [
            #  username    password  role       full_name               group  lec_sc
            ("student1", "stu123",  "student", "Amara Osei",           g1,    None),
            ("student2", "stu456",  "student", "Kofi Mensah",          g1,    None),
            ("teacher1", "teach1",  "teacher", "Dr. Lawrence Nderu",   None,  "l1"),
            ("teacher2", "teach2",  "teacher", "Dr. P. Murithi",       None,  "l2"),
            ("rep1",     "rep123",  "rep",     "Zara Kariuki",         g1,    None),
        ]
        user_map = {}
        for uname, pwd, role, full_name, grp, lsc in user_rows:
            u = User(
                username    = uname,
                role        = role,
                full_name   = full_name,
                group_id    = grp.id if grp else None,
                lecturer_id = lec_map[lsc].id if lsc else None,
            )
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            user_map[uname] = u
        print(f"✓ {len(user_rows)} users")

        # ── Classes ───────────────────────────────────────────────────────
        class_rows = [
            ("c1","l1","Monday",    "11:00","12:00","JKAC 003"),
            ("c1","l1","Monday",    "12:00","13:00","SCC 108"),
            ("c2","l2","Tuesday",   "07:00","08:00","CTC 03"),
            ("c2","l2","Tuesday",   "09:00","10:00","H7 029"),
            ("c3","l3","Tuesday",   "11:00","12:00","H7 029"),
            ("c3","l3","Tuesday",   "13:00","14:00","HRD 305"),
            ("c4","l4","Wednesday", "07:00","08:00","HRD 206"),
            ("c4","l4","Wednesday", "09:00","10:00","SCC 108"),
            ("c5","l5","Wednesday", "12:00","13:00","ELB 014"),
            ("c5","l5","Wednesday", "15:00","16:00","CTC 202"),
            ("c6","l6","Thursday",  "07:00","08:00","SCC 006"),
            ("c6","l6","Thursday",  "09:00","10:00","SCC 108"),
            ("c7","l7","Thursday",  "12:00","13:00","HRD 110"),
            ("c7","l7","Thursday",  "15:00","16:00","SCC 108"),
            ("c8","l8","Friday",    "10:00","11:00","HRD 20"),
        ]
        slot_objs = []
        for cid, lsc, day, start, end, venue in class_rows:
            slot = ClassSlot(
                course_id   = course_map[cid].id,
                lecturer_id = lec_map[lsc].id,
                group_id    = g1.id,
                day         = day,
                start_time  = start,
                end_time    = end,
                venue       = venue,
            )
            db.session.add(slot)
            db.session.flush()
            slot_objs.append(slot)
        print(f"✓ {len(slot_objs)} class slots")

        cl1, cl2 = slot_objs[0], slot_objs[1]

        # ── Reviews ───────────────────────────────────────────────────────
        review_rows = [
            (cl1, "student1", "l1",  None,       5, "Excellent class, very engaging!"),
            (cl2, "student2", "l2",  None,       4, "Good explanation of algorithms."),
            (cl1, "teacher1",  None, "student1", 4, "Active participation."),
        ]
        for slot, from_u, to_lsc, to_u, rating, comment in review_rows:
            r = Review(
                class_id       = slot.id,
                from_user_id   = user_map[from_u].id,
                to_lecturer_id = lec_map[to_lsc].id  if to_lsc else None,
                to_user_id     = user_map[to_u].id    if to_u   else None,
                rating         = rating,
                comment        = comment,
            )
            db.session.add(r)
        print("✓ 3 reviews")

        # ── Notifications ─────────────────────────────────────────────────
        notif_rows = [
            ("student1","reminder",     "Class starting soon: ICS2207 with Dr. Lawrence Nderu at JKAC 003", True),
            ("student1","announcement", "Assignment 2 deadline: 23 Feb 2025 at midnight",                    False),
            ("student1","reminder",     "Class starting soon: ICS2210 with Dr. P. Murithi at CTC 03",       False),
            ("student2","reminder",     "Class starting soon: ICS2207 with Dr. Lawrence Nderu at JKAC 003", False),
            ("rep1",    "announcement", "Assignment 2 deadline: 23 Feb 2025 at midnight",                    False),
        ]
        for uname, ntype, text, is_read in notif_rows:
            db.session.add(Notification(user_id=user_map[uname].id,
                                        type=ntype, text=text, is_read=is_read))
        print("✓ 5 notifications")

        # ── Announcements ─────────────────────────────────────────────────
        ann_rows = [
            ("rep1","Assignment 2 Deadline","deadline",
             "Assignment 2 is due 23 Feb 2025 at midnight. Submit via LMS."),
            ("rep1","Public Holiday","holiday",
             "No classes on Friday 16 Feb. Enjoy the long weekend!"),
        ]
        for uname, title, atype, body in ann_rows:
            db.session.add(Announcement(group_id=g1.id, posted_by=user_map[uname].id,
                                        title=title, type=atype, body=body))
        print("✓ 2 announcements")

        # ── Resources ─────────────────────────────────────────────────────
        res_rows = [
            ("rep1","ICS2207 Week 3 Slides","c1","https://drive.google.com"),
            ("rep1","DSA Practice Problems", "c2","https://drive.google.com"),
        ]
        for uname, title, cid, link in res_rows:
            db.session.add(Resource(title=title, course_id=course_map[cid].id,
                                    added_by=user_map[uname].id, link=link))
        print("✓ 2 resources")

        # ── User settings ─────────────────────────────────────────────────
        for u in user_map.values():
            s = UserSettings(user_id=u.id)
            s.data = {"leadTime": 30, "toast": True, "sound": False}
            db.session.add(s)
        print("✓ Settings for all users")

        db.session.commit()
        print("\n🌿 Database seeded successfully!")
        print("─" * 38)
        print("  student1 / stu123  →  Student")
        print("  student2 / stu456  →  Student")
        print("  teacher1 / teach1  →  Teacher")
        print("  teacher2 / teach2  →  Teacher")
        print("  rep1     / rep123  →  Class Rep")


if __name__ == "__main__":
    seed()