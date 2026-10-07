from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.substitutions import Command
from launch_ros.actions import Node


def generate_launch_description():
    description_share = Path(
        get_package_share_directory("turtlebot3_description")
    )
    fake_share = Path(
        get_package_share_directory("turtlebot3_fake_node")
    )
    custom_share = Path(
        get_package_share_directory("tb3_deadman_teleop")
    )

    urdf = description_share / "urdf" / "turtlebot3_burger.urdf"
    fake_param = fake_share / "param" / "burger.yaml"
    rviz_config = custom_share / "rviz" / "tb3_deadman.rviz"

    robot_description = Command(
        [
            "xacro ",
            str(urdf),
            " namespace:=",
        ]
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable("TURTLEBOT3_MODEL", "burger"),

            Node(
                package="turtlebot3_fake_node",
                executable="turtlebot3_fake_node",
                name="turtlebot3_fake_node",
                output="screen",
                parameters=[str(fake_param)],
            ),

            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "robot_description": robot_description,
                    }
                ],
            ),

            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", str(rviz_config)],
            ),

            Node(
                package="tb3_deadman_teleop",
                executable="deadman_teleop",
                name="tb3_deadman_teleop",
                output="screen",
            ),
        ]
    )
