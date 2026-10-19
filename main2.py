"""Application entry point."""
import sys

from PyQt5 import QtWidgets

from fb_automation.logging_config import setup_logging
from fb_automation.ui.main_window import Ui_MainWindow


class App(QtWidgets.QMainWindow, Ui_MainWindow):
    """Main window — wires the generated UI with the application logic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def closeEvent(self, event):
        """Ensure threads and the browser are shut down cleanly."""
        try:
            if getattr(self, "task_execute", None) is not None:
                self.task_execute.stop()
                self.task_execute.wait(3000)
            if getattr(self, "bot", None) is not None:
                self.bot.close()
        finally:
            super().closeEvent(event)


if __name__ == "__main__":
    setup_logging()
    app = QtWidgets.QApplication(sys.argv)
    form = App()
    form.show()
    sys.exit(app.exec_())