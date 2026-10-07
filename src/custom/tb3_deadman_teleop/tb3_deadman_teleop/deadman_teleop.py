#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


LINEAR_SPEED = 0.18
ANGULAR_SPEED = 1.50
PUBLISH_HZ = 20.0


class TeleopNode(Node):
    def __init__(self):
        super().__init__("tb3_deadman_teleop")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.linear = 0.0
        self.angular = 0.0

    def publish_command(self):
        msg = Twist()
        msg.linear.x = float(self.linear)
        msg.angular.z = float(self.angular)
        self.publisher.publish(msg)

    def hard_stop(self):
        self.linear = 0.0
        self.angular = 0.0

        # Make the zero command the unambiguous last command.
        for _ in range(5):
            self.publish_command()


class DeadmanWindow(QWidget):
    FORWARD = {Qt.Key_W, Qt.Key_Up}
    BACKWARD = {Qt.Key_S, Qt.Key_Down}
    LEFT = {Qt.Key_A, Qt.Key_Left}
    RIGHT = {Qt.Key_D, Qt.Key_Right}
    CONTROL_KEYS = FORWARD | BACKWARD | LEFT | RIGHT

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.held = set()

        self.setWindowTitle("TurtleBot3 Burger — DEAD-MAN TELEOP")
        self.setMinimumWidth(480)
        self.setFocusPolicy(Qt.StrongFocus)

        title = QLabel("TurtleBot3 Burger — DEAD-MAN")
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
            "ESC       : Quit"
        )

        self.status = QLabel()
        self.status.setFont(QFont("Monospace", 13))

        safety = QLabel("DEAD-MAN RELEASE STOP ACTIVE")
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
        self.timer.start(int(1000.0 / PUBLISH_HZ))

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
        moving = abs(self.node.linear) > 1e-9 or abs(self.node.angular) > 1e-9
        state = "MOVING — HOLD KEY" if moving else "STOPPED"

        self.status.setText(
            f"linear  : {self.node.linear:+.3f} m/s\n"
            f"angular : {self.node.angular:+.3f} rad/s\n"
            f"state   : {state}"
        )

    def recalculate(self):
        linear, angular = self.calculate()
        self.node.linear = linear
        self.node.angular = angular
        self.node.publish_command()
        self.refresh_status()

    def keyPressEvent(self, event):
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
            self.close()
            event.accept()
            return

        if key in self.CONTROL_KEYS:
            self.held.add(key)
            self.recalculate()
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
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
        # Losing keyboard focus is a safety stop.
        self.held.clear()
        self.node.hard_stop()
        self.refresh_status()
        super().focusOutEvent(event)

    def tick(self):
        # While stopped, explicit zero velocity continues to be published.
        self.node.publish_command()
        rclpy.spin_once(self.node, timeout_sec=0.0)

    def closeEvent(self, event):
        self.held.clear()
        self.node.hard_stop()
        event.accept()


def main(args=None):
    rclpy.init(args=args)
    node = TeleopNode()

    app = QApplication(sys.argv)
    window = DeadmanWindow(node)
    window.show()
    window.raise_()
    window.activateWindow()
    window.setFocus()

    rc = app.exec_()

    node.hard_stop()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
