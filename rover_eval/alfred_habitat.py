"""Alfred's navigation stack (dimos/robot/diy/alfred/blueprints/_nav.py) driven by Habitat.

Real alfred: Mid-360 -> Point-LIO -> RayTracingVoxelMap -> MLS -> LocalPlanner -> follower.
Here Habitat stands in for the hardware and Point-LIO: its depth camera is the scan and
its pose is ground truth on tf. The planners, follower and MovementManager are alfred's,
with alfred's embodiment and constants. Only the frame names change: habitat's root is
`world`, alfred's is `odom`.

Run in a clean shell:
    bash --noprofile --norc
    . rover_eval/env.sh
    python rover_eval/alfred_habitat.py
"""

from functools import partial

from dimos.core.coordination.blueprints import autoconnect
from dimos.core.coordination.module_coordinator import ModuleCoordinator
from dimos.core.global_config import global_config
from dimos.mapping.ray_tracing.module import RayTracingVoxelMap
from dimos.navigation.embodiment.alfred import ALFRED
from dimos.navigation.global_planner.mls_planner.mls_planner_native import MLSPlannerNative
from dimos.navigation.global_planner.mls_planner.viz import planner_visual_override
from dimos.navigation.local_planner.native import LocalPlannerNative
from dimos.navigation.local_planner.viz import motion_visual_override
from dimos.navigation.movement_manager.movement_manager import MovementManager
from dimos.navigation.trajectory_follower.fancy.native import TrajectoryFollowerNative
from dimos.robot.diy.alfred.blueprints._nav import (
    PLANNER_VIZ_HZ,
    STEP_THRESHOLD_M,
    VOXEL_SIZE_METERS,
    WALL_CLEARANCE_M,
    _path_colored,
)
from dimos.simulation.habitat.blueprints import _rerun_config
from dimos.simulation.habitat.connection import HabitatConnection
from dimos.visualization.vis_module import vis_module

WORLD_FRAME = "world"
SCAN_TOPIC = "habitat_scan"
# The depth camera's reach stands in for alfred's 15 m lidar range.
MAX_DEPTH_M = 5.0
# The camera cannot tilt, and the MLS planner snaps the start to a surface cell within
# 1.5 m (planner.rs SNAP_SEARCH_RADIUS_M): the floor must be seen that close. At 1.0 m
# with a 90 deg hfov the nearest floor seen was 1.74 m out and every plan failed.
# 0.45 m (habitat's default, near the Mid-360's 0.3 m) with a 110 deg hfov (about
# +-38 deg vertical at 16:9) sees the floor from about 0.6 m.
CAMERA_HEIGHT_M = 0.45
HFOV_DEG = 110.0

alfred_habitat = autoconnect(
    HabitatConnection.blueprint(
        publish_scan=True,
        scan_frame="camera_optical",  # the ray tracer wants the sensor frame
        camera_height_m=CAMERA_HEIGHT_M,
        hfov_deg=HFOV_DEG,
        max_depth_m=MAX_DEPTH_M,
    ).remappings([(HabitatConnection, "registered_scan", SCAN_TOPIC)]),
    # Alfred's map and planners, as in _alfred_nav, plus the world frame.
    RayTracingVoxelMap.blueprint(
        voxel_size=VOXEL_SIZE_METERS,
        max_range=MAX_DEPTH_M,
        global_emit_every=50,
        world_frame=WORLD_FRAME,
    ).remappings([(RayTracingVoxelMap, "lidar", SCAN_TOPIC)]),
    MLSPlannerNative.blueprint(
        world_frame=WORLD_FRAME,
        start_z_offset_m=0.0,  # habitat's base_link sits on the navmesh
        voxel_size=VOXEL_SIZE_METERS,
        robot_height=ALFRED.height,
        wall_clearance_m=WALL_CLEARANCE_M,
        step_threshold_m=STEP_THRESHOLD_M,
        step_penalty_weight=1.0,
        viz_publish_hz=PLANNER_VIZ_HZ,
    ).remappings(
        [
            (MLSPlannerNative, "global_map", "global_map_unused"),
            (MLSPlannerNative, "path", "planner_path"),
        ]
    ),
    LocalPlannerNative.blueprint(embodiment=ALFRED, step_speed=0.2, world_frame=WORLD_FRAME),
    TrajectoryFollowerNative.blueprint(embodiment=ALFRED),
    # Click -> goal, keys -> tele_cmd_vel (cancels the goal), nav/tele mux -> cmd_vel.
    MovementManager.blueprint(),
    vis_module(
        global_config.viewer,
        rerun_config=_rerun_config(
            {
                "world/planner_path": partial(_path_colored, color=(170, 60, 220)),
                **motion_visual_override(embodiment=ALFRED),
                **planner_visual_override(
                    PLANNER_VIZ_HZ, VOXEL_SIZE_METERS, WALL_CLEARANCE_M
                ),
            }
        ),
    ),
).global_config(transport="zenoh")

if __name__ == "__main__":
    ModuleCoordinator.build(alfred_habitat).loop()
