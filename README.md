# TurtleBot3 Humble Dead-Man Baseline

Minimal rebuildable source repository for the verified TurtleBot3 Burger
ROS 2 Humble basic environment.

## What is stored here

Only the important custom source and rebuild metadata:

- `src/custom/tb3_deadman_teleop`
- exact ROBOTIS commit lock (`UPSTREAM_LOCK.tsv`)
- `rebuild.sh`
- `verify.sh`
- `run.sh`
- source integrity manifest (`SOURCE_SHA256.txt`)

The ROBOTIS repositories themselves are **not duplicated into GitHub**.

## Verified behavior

- TurtleBot3 Burger fake node
- `robot_state_publisher`
- RViz2
- `/cmd_vel`
- `/odom`
- `/joint_states`
- `/tf`, `/tf_static`
- Odometry display `Keep = 1`
- W/A/S/D and arrow-key dead-man control
- releasing the key immediately commands zero velocity
- losing keyboard focus immediately commands zero velocity
- SPACE performs an immediate stop

## Target platform

- Ubuntu 22.04
- ROS 2 Humble
- TurtleBot3 Burger

## Fresh rebuild

```bash
chmod +x rebuild.sh verify.sh run.sh
./rebuild.sh
./verify.sh
./run.sh
```

`rebuild.sh` clones the exact ROBOTIS commits stored in
`UPSTREAM_LOCK.tsv`, so the source baseline is reproducible.

## Controls

| Key | Action |
| --- | --- |
| W / Up | Forward while held |
| S / Down | Reverse while held |
| A / Left | Turn left while held |
| D / Right | Turn right while held |
| Release | Stop corresponding motion |
| Space | Immediate full stop |
| Esc | Exit |

## Gazebo policy

This baseline deliberately does **not** install Gazebo Classic.

The verified host already uses GZ Harmonic / `gz-tools2`, which conflicts
at the APT-package level with Gazebo Classic 11. The fake-node + RViz
baseline therefore stays independent of Gazebo Classic.

## One-shot lifecycle

The baseline uses one-shot shutdown semantics.

- Normal startup remains alive continuously.
- Releasing W/A/S/D stops velocity but does not exit.
- Losing keyboard focus stops velocity but does not exit.
- Closing the dead-man window, pressing `Esc`, closing RViz, or pressing
  `Ctrl+C` shuts down the complete launch stack.
- SIGINT/SIGTERM are bridged into the Qt event loop through a nonblocking
  self-pipe and `QSocketNotifier`.
- The periodic `/cmd_vel` timer is stopped before ROS teardown.
- A final zero `/cmd_vel` is attempted before node destruction.
- RViz and dead-man `OnProcessExit` events request LaunchService shutdown.

Regression test:

```bash
./shutdown_smoke_test.sh
```

The test proves at least three seconds of startup survival, sends exactly one
SIGINT directly to the installed dead-man executable, and requires exit within
two seconds without `RCLError`, traceback, or SIGKILL escalation.
