# Source in a clean shell, from anywhere:
#   bash --noprofile --norc
#   . <repo>/rover_eval/env.sh
# Tools, caches and toolchains live next to the clone, in its parent directory. No ROS.
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export REPO
export DT=$(dirname "$REPO")
unset PYTHONPATH AMENT_PREFIX_PATH ROS_DISTRO ROS_VERSION ROS_PYTHON_VERSION CMAKE_PREFIX_PATH
export UV_CACHE_DIR=$DT/cache/uv
export UV_PYTHON_INSTALL_DIR=$DT/tools/python
export UV_TOOL_DIR=$DT/tools/uv-tools
export RUSTUP_HOME=$DT/tools/rustup
export CARGO_HOME=$DT/tools/cargo
export MAMBA_ROOT_PREFIX=$REPO/target/habitat/mm
export XDG_CACHE_HOME=$DT/cache/xdg
# libturbojpeg from conda-forge (no apt); dir holds only that one .so so nothing else is shadowed
export LD_LIBRARY_PATH=$DT/tools/turbojpeg
export PATH=$DT/tools/bin:$CARGO_HOME/bin:$REPO/.venv/bin:/usr/local/bin:/usr/bin:/bin
