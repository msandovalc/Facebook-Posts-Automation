"""QThread that runs scheduled tasks. Interruptible and thread-safe."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime as dt

from PyQt5.QtCore import QMutex, QThread, pyqtSignal

from fb_automation.services.bot import Bot

logger = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: int
    task_name: str
    user_name: str
    password: str
    targets: list
    post: tuple
    date: str
    status: str = "Init"

    def waiting_seconds(self) -> float:
        """Seconds until this task should execute (may be negative)."""
        target = dt.strptime(self.date, "%d/%m/%y %H:%M:%S")
        return (target - dt.now()).total_seconds()

    # ---- Legacy accessors (kept for backwards compatibility with older callers) ----
    def get_task_id(self) -> int:
        return self.task_id

    def get_task_name(self) -> str:
        return self.task_name

    def get_user_name(self) -> str:
        return self.user_name

    def get_password(self) -> str:
        return self.password

    def get_targets(self) -> list:
        return self.targets

    def get_post(self) -> tuple:
        return self.post

    def get_date(self) -> str:
        return self.date

    def get_status(self) -> str:
        return self.status

    def set_status(self, status: str) -> None:
        self.status = status


class TaskExecuteThread(QThread):
    stopped_signal = pyqtSignal()
    started_signal = pyqtSignal()
    task_added_signal = pyqtSignal(str)
    task_removed_signal = pyqtSignal(str)
    task_completed_signal = pyqtSignal(str)
    task_timeout_signal = pyqtSignal(str)
    task_not_found_signal = pyqtSignal()

    def __init__(self, poll_interval: float = 15):
        super().__init__()
        self.tasks: list[Task] = []
        self.lock = QMutex()
        self.poll_interval = poll_interval
        self._bot: Bot | None = None
        self._running = False

    # ---------- lifecycle ----------

    def run(self):
        self.started_signal.emit()
        logger.info("Task runner started")
        self._running = True
        try:
            # NOTE: We intentionally do NOT use isInterruptionRequested() here.
            # Qt never clears that flag across stop()/start() cycles, which
            # breaks the worker after the first Stop. self._running is our
            # own resettable source of truth.
            while self._running and self.tasks:
                task = self._peek_task()
                if task is None:
                    break

                wait = task.waiting_seconds()
                if wait <= 0:
                    self._execute_task(task)
                else:
                    self._interruptible_sleep(min(wait, self.poll_interval))
        except Exception:
            logger.exception("Failure in TaskExecuteThread.run")
        finally:
            if self._bot is not None:
                try:
                    self._bot.close()
                except Exception:
                    logger.exception("Error closing runner bot")
                self._bot = None
            self._running = False
            self.stopped_signal.emit()
            logger.info("Task runner stopped")

    def stop(self):
        """Ask the worker to exit at the next safe point."""
        self._running = False
        self.requestInterruption()  # kept for Qt politeness; not used in the loop

    # ---------- public API ----------

    def add_task(self, task: Task) -> None:
        if task.waiting_seconds() <= 0:
            self.task_timeout_signal.emit(task.task_name)
            return
        task.status = "Pending"
        self.lock.lock()
        try:
            self.tasks.append(task)
            self.tasks.sort(key=lambda t: dt.strptime(t.date, "%d/%m/%y %H:%M:%S"))
        finally:
            self.lock.unlock()
        self.task_added_signal.emit(task.task_name)
        logger.info("Task added: %s @ %s", task.task_name, task.date)
        if not self.isRunning():
            self.start()

    def remove_task(self, task: Task) -> None:
        self.lock.lock()
        try:
            found = task in self.tasks
            if found:
                self.tasks.remove(task)
        finally:
            self.lock.unlock()
        if found:
            self.task_removed_signal.emit(task.task_name)
            logger.info("Task removed: %s", task.task_name)
        else:
            self.task_not_found_signal.emit()

    def get_task_by_name(self, name: str) -> Task | None:
        self.lock.lock()
        try:
            for t in self.tasks:
                if t.task_name == name:
                    return t
            return None
        finally:
            self.lock.unlock()

    # ---------- internals ----------

    def _peek_task(self) -> Task | None:
        self.lock.lock()
        try:
            return self.tasks[0] if self.tasks else None
        finally:
            self.lock.unlock()

    def _execute_task(self, task: Task) -> None:
        self.lock.lock()
        try:
            if task in self.tasks:
                self.tasks.remove(task)
        finally:
            self.lock.unlock()

        logger.info("Executing task: %s", task.task_name)
        try:
            # Guard against orphaned tasks (post/targets deleted after scheduling)
            if task.post is None:
                logger.error("Task %s has no post attached, skipping", task.task_name)
                return
            if not task.targets:
                logger.error("Task %s has no targets, skipping", task.task_name)
                return

            if self._bot is None:
                self._bot = Bot(headless=True)
            else:
                self._bot.check_browser_state()

            # Accept both fresh login and already-active session
            login_result = self._bot.doLogin(task.user_name, task.password)
            if login_result not in ("Login Successful", "Already logged in"):
                logger.error("Login failed for task %s: %s", task.task_name, login_result)
                return

            post = task.post  # (id, msg, media, owner_id)
            for target in task.targets:  # (id, url, owner_id)
                logger.info("Posting to %s ...", target[1])
                self._bot.postToUrl(
                    message=post[1], media_path=post[2], url=target[1]
                )

            task.status = "completed"
            self.task_completed_signal.emit(task.task_name)
            self._bot.logout()
        except Exception:
            logger.exception("Error while executing task %s", task.task_name)

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep in 100 ms slices so a stop() is honoured within ~100 ms."""
        total = int(seconds * 10)
        for _ in range(total):
            if not self._running:
                return
            self.msleep(100)