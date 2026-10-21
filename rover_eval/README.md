# rover_eval: DimOS + Habitat без sudo, Nix и ROS

Оценка DimOS как альтернативы Nav2. Здесь лежит то, чего нет в upstream:

- `env.sh`: окружение, при котором все инструменты и кэши живут рядом с клоном, а не в системе.
- `alfred_habitat.py`: навигационный стек робота alfred (`dimos/robot/diy/alfred/blueprints/_nav.py`)
  поверх симулятора Habitat вместо реального железа.

Проверено на Ubuntu 22.04, RTX 3050 (драйвер 580), Python 3.12.

## Установка

Upstream собирает нативные модули через Nix, а `scripts/install.sh` вызывает apt и sudo.
Обе вещи здесь обходятся: каждый native-модуль — это обычный Cargo-крейт, а Habitat берёт из Nix
только `micromamba`.

```bash
bash --noprofile --norc               # чистый шелл: PYTHONPATH от ROS ломает venv
. rover_eval/env.sh
mkdir -p $DT/tools/bin

# uv и micromamba в $DT/tools/bin
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$DT/tools/bin UV_NO_MODIFY_PATH=1 sh
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C $DT/tools bin/micromamba

# Python-окружение
cd $REPO && uv sync --python 3.12 --extra visualization

# libturbojpeg: без неё вьюер не может закодировать кадр камеры
micromamba create -y -r $DT/tools/mamba -p $DT/tools/jpeg -c conda-forge libjpeg-turbo
mkdir -p $DT/tools/turbojpeg
ln -sf $DT/tools/jpeg/lib/libturbojpeg.so.0.5.0 $DT/tools/turbojpeg/libturbojpeg.so.0

# Rust и native-модули. Бинарники попадают в общий $REPO/target/release (.cargo/config.toml).
curl --proto =https --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal
for spec in \
    "dimos/mapping/ray_tracing/rust voxel_ray_tracing" \
    "dimos/navigation/global_planner/mls_planner/rust mls_planner" \
    "dimos/navigation/local_planner/rust local_planner --features module" \
    "dimos/navigation/trajectory_follower/fancy/rust trajectory_follower --features module"; do
  set -- $spec; dir=$1; bin=$2; shift 2
  (cd $REPO/$dir && cargo build --release --bins "$@")
  # NativeModule ищет result/bin/<bin> (выход nix build); если файл есть, сборка пропускается.
  mkdir -p $REPO/$dir/result/bin && ln -sf $REPO/target/release/$bin $REPO/$dir/result/bin/$bin
done

# Habitat: conda-окружение на Python 3.9 и сцена HM3D, всё в $REPO/target/habitat
cd $REPO/dimos/simulation/habitat/nix && ./install.sh
```

`local_planner` и `trajectory_follower` без `--features module` молча собираются только как
библиотеки, бинарников не будет.

## Запуск

```bash
bash --noprofile --norc && . rover_eval/env.sh && cd $REPO
dimos --no-build-native run habitat-nav      # upstream: MLS + BasicPathFollower
python rover_eval/alfred_habitat.py          # стек alfred: MLS + LocalPlanner + fancy follower
dimos stop
```

Цель задаётся кликом по поверхности в 3D-виде. Клавиатура — телеоп; в стеке alfred
`MovementManager` при нажатии клавиши отменяет цель.

## Что выяснилось

- **Пол должен быть виден в пределах 1.5 м от робота.** MLS привязывает старт к ячейке поверхности
  в этом радиусе (`SNAP_SEARCH_RADIUS_M` в `mls_planner/rust/src/planner.rs`). Камера Habitat
  не наклоняется: на высоте 1.0 м с hfov 90° ближайший видимый пол был в 1.74 м, и не строился
  ни один путь. Поэтому в `alfred_habitat.py` стоит высота 0.45 м и hfov 110°.
- **Неизвестное пространство непроходимо.** Карта хранит только занятые воксели, а MLS строит
  поверхности только по увиденному полу.
- **Корпус alfred строже MLS.** MLS держит от стен 0.2 м, а локальный планировщик проверяет
  корпус 0.54 × 0.53 м плюс зону комфорта 0.4 м. Глобальный путь может пройти там, где локальный
  откажет: тогда он публикует путь из одной позы, и робот стоит.

## Открытые вопросы

- В последнем тесте робот стоял на (−3.23, 1.68), и цель в 2.5 м на открытом полу так и не получила
  глобального пути (`planner_path` пустой 25 с). Причина не выяснена.
- Habitat даёт идеальную позу, поэтому SLAM-цепочку alfred (Point-LIO + релокализация)
  здесь проверить нельзя. Для этого нужна запись с Mid-360.
