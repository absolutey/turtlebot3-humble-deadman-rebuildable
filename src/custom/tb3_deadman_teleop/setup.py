from glob import glob
import os

from setuptools import setup


package_name = "tb3_deadman_teleop"

setup(
    name=package_name,
    version="1.0.3",
    packages=[package_name],
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            os.path.join("share", package_name, "launch"),
            glob("launch/*.launch.py"),
        ),
        (
            os.path.join("share", package_name, "rviz"),
            glob("rviz/*.rviz"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    description="TurtleBot3 Burger dead-man keyboard teleoperation",
    license="MIT",
    entry_points={
        "console_scripts": [
            "deadman_teleop = tb3_deadman_teleop.deadman_teleop:main",
        ],
    },
)
