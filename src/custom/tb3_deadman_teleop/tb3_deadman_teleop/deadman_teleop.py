#!/usr/bin/env python3

import signal
import socket
import sys

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

try:
    from rclpy._rclpy_pybind11 import RCLError
except ImportError:
    RCLError = RuntimeError

from geometry_msgs.msg import Twist

from PyQt5.QtCore import Qt, QTimer, QSocketNotifier
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


LINEAR_SPEED = 0.18
ANGULAR_SPEED = 1.50
PUBLISH_HZ = 20.0


def inert_signal_handler(_signum, _frame):
    # signal.set_wakeup_fd() performs the actual Qt wake-up.
    # The Python handler intentionally performs no ROS/Qt work.
    return


class TeleopNode(Node):
    def __init__(self):
        super().__init__("tb3_deadman_teleop")

        self.publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10,
        )

        self.linear = 0.0
        self.angular = 0.0

    def publish_command(self):
        msg = Twist()
        msg.linear.x = float(self.linear)
        msg.angular.z = float(self.angular)

        try:
            self.publisher.publish(msg)
            return True
        except (RCLError, RuntimeError):
            # A launch-wide shutdown can invalidate another ROS entity
            # concurrently. Do not turn that normal race into traceback spam.
            return False

    def hard_stop(self):
        self.linear = 0.0
        self.angular = 0.0

        for _ in range(3):
            if not self.publish_command():
                break


class DeadmanWindow(QWidget):
    FORWARD = {Qt.Key_W, Qt.Key_Up}
    BACKWARD = {Qt.Key_S, Qt.Key_Down}
    LEFT = {Qt.Key_A, Qt.Key_Left}
    RIGHT = {Qt.Key_D, Qt.Key_Right}

    CONTROL_KEYS = FORWARD | BACKWARD | LEFT | RIGHT

    def __init__(self, node, signal_reader):
        super().__init__()

        self.node = node
        self.signal_reader = signal_reader

        self.held = set()
        self.shutdown_started = False

        self.setWindowTitle(
            "TurtleBot3 Burger — DEAD-MAN TELEOP"
        )

        self.setMinimumWidth(480)
        self.setFocusPolicy(Qt.StrongFocus)

        title = QLabel(
            "TurtleBot3 Burger — DEAD-MAN"
        )

        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)

        help_label = QLabel(
            "Hold key = MOVE / Release key = STOP\n\n"
            "W / Up    : Forward\n"
            "S / Down  : Backward\n"
            "A / Left  : Turn left\n"
            "D / Right : Turn right\n\n"
            "SPACE     : Immediate stop\n"
            "ESC       : Close full TurtleBot3 stack\n"
            "Ctrl+C    : Close full TurtleBot3 stack"
        )

        self.status = QLabel()
        self.status.setFont(
            QFont("Monospace", 13)
        )

        safety = QLabel(
            "DEAD-MAN RELEASE STOP ACTIVE"
        )

        safety_font = QFont()
        safety_font.setPointSize(13)
        safety_font.setBold(True)
        safety.setFont(safety_font)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(help_label)
        layout.addWidget(self.status)
        layout.addWidget(safety)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(
            int(1000.0 / PUBLISH_HZ)
        )

        self.signal_notifier = QSocketNotifier(
            self.signal_reader.fileno(),
            QSocketNotifier.Read,
            self,
        )

        self.signal_notifier.activated.connect(
            self.handle_signal_fd
        )

        self.recalculate()

    def calculate(self):
        forward = bool(self.held & self.FORWARD)
        backward = bool(self.held & self.BACKWARD)
        left = bool(self.held & self.LEFT)
        right = bool(self.held & self.RIGHT)

        linear = 0.0
        angular = 0.0

        if forward and not backward:
            linear = LINEAR_SPEED
        elif backward and not forward:
            linear = -LINEAR_SPEED

        if left and not right:
            angular = ANGULAR_SPEED
        elif right and not left:
            angular = -ANGULAR_SPEED

        return linear, angular

    def refresh_status(self):
        moving = (
            abs(self.node.linear) > 1e-9
            or abs(self.node.angular) > 1e-9
        )

        state = (
            "MOVING — HOLD KEY"
            if moving
            else "STOPPED"
        )

        self.status.setText(
            f"linear  : {self.node.linear:+.3f} m/s\n"
            f"angular : {self.node.angular:+.3f} rad/s\n"
            f"state   : {state}"
        )

    def recalculate(self):
        if self.shutdown_started:
            return

        linear, angular = self.calculate()
        self.node.linear = linear
        self.node.angular = angular

        self.node.publish_command()
        self.refresh_status()

    def handle_signal_fd(self, *_args):
        # Drain every pending signal byte.
        while True:
            try:
                data = self.signal_reader.recv(4096)
                if not data:
                    break
            except BlockingIOError:
                break

        self.begin_shutdown()

    def begin_shutdown(self):
        if self.shutdown_started:
            return

        self.shutdown_started = True

        # The critical ordering:
        # 1. no more periodic callbacks
        # 2. no more signal callbacks
        # 3. zero velocity, best effort
        # 4. exit Qt event loop
        if self.timer.isActive():
            self.timer.stop()

        if self.signal_notifier.isEnabled():
            self.signal_notifier.setEnabled(False)

        self.held.clear()

        self.node.hard_stop()
        self.refresh_status()

        app = QApplication.instance()

        if app is not None:
            app.quit()

    def keyPressEvent(self, event):
        if self.shutdown_started:
            event.accept()
            return

        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()

        if key == Qt.Key_Space:
            self.held.clear()
            self.node.hard_stop()
            self.refresh_status()
            event.accept()
            return

        if key == Qt.Key_Escape:
            self.begin_shutdown()
            event.accept()
            return

        if key in self.CONTROL_KEYS:
            self.held.add(key)
            self.recalculate()
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.shutdown_started:
            event.accept()
            return

        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()

        if key in self.CONTROL_KEYS:
            self.held.discard(key)
            self.recalculate()
            event.accept()
            return

        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        # Focus loss is STOP only; it must never exit the program.
        if not self.shutdown_started:
            self.held.clear()
            self.node.hard_stop()
            self.refresh_status()

        super().focusOutEvent(event)

    def tick(self):
        if self.shutdown_started:
            return

        self.node.publish_command()

    def closeEvent(self, event):
        # Window X is an explicit stack-exit request.
        if not self.shutdown_started:
            self.shutdown_started = True

            if self.timer.isActive():
                self.timer.stop()

            if self.signal_notifier.isEnabled():
                self.signal_notifier.setEnabled(False)

            self.held.clear()
            self.node.hard_stop()

        event.accept()


def main(args=None):
    signal_reader = None
    signal_writer = None
    old_wakeup_fd = -1

    # We own SIGINT/SIGTERM ordering for this process.
    rclpy.init(
        args=args,
        signal_handler_options=SignalHandlerOptions.NO,
    )

    node = TeleopNode()

    try:
        # Self-pipe for immediate POSIX-signal -> Qt wake-up.
        signal_reader, signal_writer = socket.socketpair()

        signal_reader.setblocking(False)
        signal_writer.setblocking(False)

        old_wakeup_fd = signal.set_wakeup_fd(
            signal_writer.fileno()
        )

        signal.signal(
            signal.SIGINT,
            inert_signal_handler,
        )

        signal.signal(
            signal.SIGTERM,
            inert_signal_handler,
        )

        # ROS launch adds --ros-args etc. Qt must never parse them.
        app = QApplication(
            [sys.argv[0]]
        )

        app.setQuitOnLastWindowClosed(True)

        window = DeadmanWindow(
            node,
            signal_reader,
        )

        window.show()
        window.raise_()
        window.activateWindow()
        window.setFocus()

        rc = app.exec_()

        if window.timer.isActive():
            window.timer.stop()

        if window.signal_notifier.isEnabled():
            window.signal_notifier.setEnabled(False)

        return rc

    finally:
        # Disable signal->fd writes before closing the sockets.
        try:
            signal.set_wakeup_fd(
                old_wakeup_fd
            )
        except (ValueError, OSError):
            pass

        node.hard_stop()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

        if signal_reader is not None:
            signal_reader.close()

        if signal_writer is not None:
            signal_writer.close()


if __name__ == "__main__":
    raise SystemExit(main())
