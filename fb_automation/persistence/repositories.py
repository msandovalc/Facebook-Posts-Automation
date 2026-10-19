"""
Per-entity repositories + DatabaseService (facade) which keeps the old
DatabaseWrapper API so the UI doesn't need to change.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from .database import Database
from .encryption import DatabaseEncrypt

logger = logging.getLogger(__name__)


# ---------- DTOs ----------

@dataclass(frozen=True)
class User:
    id: int
    username: str
    password: str  # already decrypted


@dataclass(frozen=True)
class Post:
    id: int
    msg: str
    media: Optional[str]
    owner_id: int


@dataclass(frozen=True)
class Target:
    id: int
    url: str
    owner_id: int


@dataclass(frozen=True)
class TaskRecord:
    id: int
    name: str
    owner_id: int
    post_id: int
    target_ids: list[int]
    date: str


# ---------- Repositories ----------

class UserRepository:
    def __init__(self, db: Database, enc: DatabaseEncrypt):
        self.db, self.enc = db, enc

    def add(self, username: str, password: str) -> bool:
        if self.get_by_credentials(username, password):
            logger.info("Duplicate user: %s", username)
            return False
        with self.db.connect() as c:
            c.execute(
                "insert into users (USER_NAME,PASSWORD) values (?,?)",
                (username, self.enc.encrypt(password)),
            )
        logger.info("User added: %s", username)
        return True

    def get_by_credentials(self, username: str, password: str) -> Optional[User]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,USER_NAME,PASSWORD from users where USER_NAME=?",
                (username,),
            ).fetchone()
        if row and self.enc.decrypt(row[2]) == password:
            return User(row[0], row[1], password)
        return None

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,USER_NAME,PASSWORD from users where ID=?",
                (user_id,),
            ).fetchone()
        return User(row[0], row[1], self.enc.decrypt(row[2])) if row else None

    def get_all(self) -> list[User]:
        with self.db.connect() as c:
            rows = c.execute("select ID,USER_NAME,PASSWORD from users").fetchall()
        return [User(r[0], r[1], self.enc.decrypt(r[2])) for r in rows]

    def update(self, user_id: int, username: str, password: str) -> bool:
        with self.db.connect() as c:
            cur = c.execute(
                "update users set USER_NAME=?,PASSWORD=? where ID=?",
                (username, self.enc.encrypt(password), user_id),
            )
        return cur.rowcount > 0

    def delete(self, user_id: int) -> bool:
        with self.db.connect() as c:
            c.execute("delete from posts where OWNER_ID=?", (user_id,))
            c.execute("delete from targets where OWNER_ID=?", (user_id,))
            c.execute("delete from tasks where OWNER_ID=?", (user_id,))
            cur = c.execute("delete from users where ID=?", (user_id,))
        return cur.rowcount > 0


class PostRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, msg: str, media: Optional[str], owner_id: int) -> bool:
        if self.get(msg, media, owner_id) is not None:
            return False
        with self.db.connect() as c:
            c.execute(
                "insert into posts (MSG,MEDIA,OWNER_ID) values (?,?,?)",
                (msg, media, owner_id),
            )
        return True

    def get(self, msg: str, media: Optional[str], owner_id: int) -> Optional[Post]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,MSG,MEDIA,OWNER_ID from posts where MSG=? and MEDIA is ? and OWNER_ID=?",
                (msg, media, owner_id),
            ).fetchone()
        return Post(*row) if row else None

    def get_by_id(self, post_id: int) -> Optional[Post]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,MSG,MEDIA,OWNER_ID from posts where ID=?",
                (post_id,),
            ).fetchone()
        return Post(*row) if row else None

    def get_by_owner(self, owner_id: int) -> list[Post]:
        with self.db.connect() as c:
            rows = c.execute(
                "select ID,MSG,MEDIA,OWNER_ID from posts where OWNER_ID=?",
                (owner_id,),
            ).fetchall()
        return [Post(*r) for r in rows]

    def update(self, post_id: int, msg: str, media: Optional[str]) -> bool:
        with self.db.connect() as c:
            cur = c.execute("update posts set MSG=?,MEDIA=? where ID=?", (msg, media, post_id))
        return cur.rowcount > 0

    def delete(self, post_id: int) -> bool:
        with self.db.connect() as c:
            cur = c.execute("delete from posts where ID=?", (post_id,))
        return cur.rowcount > 0


class TargetRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, url: str, owner_id: int) -> bool:
        if self.get(url, owner_id) is not None:
            return False
        with self.db.connect() as c:
            c.execute(
                "insert into targets (TARGET_URL,OWNER_ID) values (?,?)",
                (url, owner_id),
            )
        return True

    def get(self, url: str, owner_id: int) -> Optional[Target]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,TARGET_URL,OWNER_ID from targets where TARGET_URL=? and OWNER_ID=?",
                (url, owner_id),
            ).fetchone()
        return Target(*row) if row else None

    def get_by_id(self, target_id: int) -> Optional[Target]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,TARGET_URL,OWNER_ID from targets where ID=?",
                (target_id,),
            ).fetchone()
        return Target(*row) if row else None

    def get_by_owner(self, owner_id: int) -> list[Target]:
        with self.db.connect() as c:
            rows = c.execute(
                "select ID,TARGET_URL,OWNER_ID from targets where OWNER_ID=?",
                (owner_id,),
            ).fetchall()
        return [Target(*r) for r in rows]

    def update(self, target_id: int, url: str) -> bool:
        with self.db.connect() as c:
            cur = c.execute("update targets set TARGET_URL=? where ID=?", (url, target_id))
        return cur.rowcount > 0

    def delete(self, target_id: int) -> bool:
        with self.db.connect() as c:
            cur = c.execute("delete from targets where ID=?", (target_id,))
        return cur.rowcount > 0


class TaskRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _parse_targets(raw: str) -> list[int]:
        return [int(t) for t in raw.split(",") if t.strip().isdigit()]

    def add(
        self, name: str, owner_id: int, post_id: int,
        target_ids: list[int], date: str,
    ) -> bool:
        if self.get_by_name(name, owner_id) is not None:
            return False
        raw = ",".join(str(t) for t in target_ids)
        with self.db.connect() as c:
            c.execute(
                "insert into tasks (TASK_NAME,OWNER_ID,POST_ID,TARGETS,DATE) "
                "values (?,?,?,?,?)",
                (name, owner_id, post_id, raw, date),
            )
        return True

    def get_by_name(self, name: str, owner_id: int) -> Optional[TaskRecord]:
        with self.db.connect() as c:
            row = c.execute(
                "select ID,TASK_NAME,OWNER_ID,POST_ID,TARGETS,DATE from tasks "
                "where TASK_NAME=? and OWNER_ID=?",
                (name, owner_id),
            ).fetchone()
        if not row:
            return None
        return TaskRecord(row[0], row[1], row[2], row[3], self._parse_targets(row[4]), row[5])

    def get_by_owner(self, owner_id: int) -> list[TaskRecord]:
        with self.db.connect() as c:
            rows = c.execute(
                "select ID,TASK_NAME,OWNER_ID,POST_ID,TARGETS,DATE from tasks "
                "where OWNER_ID=?",
                (owner_id,),
            ).fetchall()
        return [
            TaskRecord(r[0], r[1], r[2], r[3], self._parse_targets(r[4]), r[5])
            for r in rows
        ]

    def update(
        self, task_id: int, name: str, post_id: int,
        target_ids: list[int], date: str,
    ) -> bool:
        raw = ",".join(str(t) for t in target_ids)
        with self.db.connect() as c:
            cur = c.execute(
                "update tasks set TASK_NAME=?,POST_ID=?,TARGETS=?,DATE=? where ID=?",
                (name, post_id, raw, date, task_id),
            )
        return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        with self.db.connect() as c:
            cur = c.execute("delete from tasks where ID=?", (task_id,))
        return cur.rowcount > 0


# ---------- Facade ----------

class DatabaseService:
    """Facade exposing the original DatabaseWrapper API (UI compatibility)."""

    def __init__(self, path=None):
        self.db = Database(path) if path else Database()
        enc = DatabaseEncrypt()
        self.users = UserRepository(self.db, enc)
        self.posts = PostRepository(self.db)
        self.targets = TargetRepository(self.db)
        self.tasks = TaskRepository(self.db)

    # ---- Users ----
    def add_user(self, username: str, password: str) -> str:
        return "SUCCESS" if self.users.add(username, password) else "ERROR"

    def edit_user(self, username, password, new_username, new_password) -> str:
        u = self.users.get_by_credentials(username, password)
        if u is None:
            return "ERROR"
        return "SUCCESS" if self.users.update(u.id, new_username, new_password) else "ERROR"

    def delete_user(self, user_id) -> str:
        return "SUCCESS" if self.users.delete(int(user_id)) else "ERROR"

    def get_user(self, username, password):
        u = self.users.get_by_credentials(username, password)
        return (u.id, u.username, u.password) if u else None

    def get_user_by_id(self, user_id):
        u = self.users.get_by_id(int(user_id))
        return (u.id, u.username, u.password) if u else None

    def get_users(self):
        return [(u.id, u.username) for u in self.users.get_all()]

    # ---- Posts ----
    def add_post(self, msg, media, owner_id) -> str:
        return "SUCCESS" if self.posts.add(msg, media, int(owner_id)) else "ERROR"

    def edit_post(self, msg, media, owner_id, new_msg, new_media) -> str:
        p = self.posts.get(msg, media, int(owner_id))
        if p is None:
            return "ERROR"
        return "SUCCESS" if self.posts.update(p.id, new_msg, new_media) else "ERROR"

    def delete_post(self, msg, media, owner_id) -> str:
        p = self.posts.get(msg, media, int(owner_id))
        if p is None:
            return "ERROR"
        return "SUCCESS" if self.posts.delete(p.id) else "ERROR"

    def get_post(self, msg, media, owner_id):
        p = self.posts.get(msg, media, int(owner_id))
        return (p.id, p.msg, p.media, p.owner_id) if p else None

    def get_post_by_id(self, post_id):
        p = self.posts.get_by_id(int(post_id))
        return (p.id, p.msg, p.media, p.owner_id) if p else None

    def get_posts_by_user_id(self, owner_id):
        return [
            (p.id, p.msg, p.media, p.owner_id)
            for p in self.posts.get_by_owner(int(owner_id))
        ]

    # ---- Targets ----
    def add_target(self, url, owner_id) -> str:
        return "SUCCESS" if self.targets.add(url, int(owner_id)) else "ERROR"

    def edit_target(self, url, owner_id, new_url) -> str:
        t = self.targets.get(url, int(owner_id))
        if t is None:
            return "ERROR"
        return "SUCCESS" if self.targets.update(t.id, new_url) else "ERROR"

    def delete_target(self, url, owner_id) -> str:
        t = self.targets.get(url, int(owner_id))
        if t is None:
            return "ERROR"
        return "SUCCESS" if self.targets.delete(t.id) else "ERROR"

    def get_target(self, url, owner_id):
        t = self.targets.get(url, int(owner_id))
        return (t.id, t.url, t.owner_id) if t else None

    def get_target_by_id(self, target_id):
        t = self.targets.get_by_id(int(target_id))
        return (t.id, t.url, t.owner_id) if t else None

    def get_targets_by_user_id(self, owner_id):
        return [
            (t.id, t.url, t.owner_id)
            for t in self.targets.get_by_owner(int(owner_id))
        ]

    # ---- Tasks ----
    def _resolve_target_ids(self, targets: set[str], owner_id: int) -> list[int]:
        ids = []
        for url in targets:
            t = self.targets.get(url, owner_id)
            if t:
                ids.append(t.id)
        return ids

    def add_task(self, task_name, owner_id, post_id, targets, date) -> str:
        target_ids = self._resolve_target_ids(targets, int(owner_id))
        ok = self.tasks.add(task_name, int(owner_id), int(post_id), target_ids, date)
        return "SUCCESS" if ok else "ERROR"

    def edit_task(self, task_name, owner_id, new_name, new_post_id, new_targets, new_date) -> str:
        t = self.tasks.get_by_name(task_name, int(owner_id))
        if t is None:
            return "ERROR"
        target_ids = self._resolve_target_ids(new_targets, int(owner_id))
        ok = self.tasks.update(t.id, new_name, int(new_post_id), target_ids, new_date)
        return "SUCCESS" if ok else "ERROR"

    def delete_task(self, task_name, owner_id) -> str:
        t = self.tasks.get_by_name(task_name, int(owner_id))
        if t is None:
            return "ERROR"
        return "SUCCESS" if self.tasks.delete(t.id) else "ERROR"

    def get_task(self, task_name, owner_id):
        t = self.tasks.get_by_name(task_name, int(owner_id))
        return (
            (t.id, t.name, t.owner_id, t.post_id, ",".join(map(str, t.target_ids)), t.date)
            if t else None
        )

    def get_tasks_by_user_id(self, owner_id):
        return [
            (t.id, t.name, t.owner_id, t.post_id,
             ",".join(map(str, t.target_ids)), t.date)
            for t in self.tasks.get_by_owner(int(owner_id))
        ]

    # ---- Import ----
    def load_data(self, file_path: str, owner_id) -> str:
        try:
            with open(file_path, "rb") as f:
                data = json.loads(f.read())
            for post in data["posts"]:
                media = post["media"] if post["media"] != "" else None
                self.add_post(post["msg"], media, owner_id)
            for target in data["targets"]:
                self.add_target(target["target"], owner_id)
            return "SUCCESS"
        except (KeyError, json.JSONDecodeError):
            logger.exception("Unknown format while loading %s", file_path)
            return "ERROR"