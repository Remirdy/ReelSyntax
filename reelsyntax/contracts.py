from typing import Literal, NotRequired, TypedDict


class OutputSettings(TypedDict):
    width: int
    height: int
    fps: str


class SceneParams(TypedDict, total=False):
    heading: str
    subheading: str
    kicker: str
    background: str
    foreground: str
    accent: str
    series: list[float]
    font_mode: Literal['default', 'system']
    shot: Literal['macro', 'iris', 'assembly', 'hero']
    samples: int
    source: str
    in_frame: int
    layers: list[dict]


class CameraConfig(TypedDict, total=False):
    preset: Literal['locked', 'dolly_in', 'orbit', 'crane_rise', 'dolly_zoom']
    focal_mm: float
    position: list[float]
    target: list[float]


class TransitionConfig(TypedDict, total=False):
    type: Literal['cut', 'cross_dissolve', 'fade_black', 'wipe_left']
    duration_frames: int


class Scene(TypedDict):
    id: str
    duration_frames: int
    recipe: Literal['assembly', 'rings', 'signal', 'title', 'prism-monolith', 'kinetic-type', 'data-horizon', 'hud-lock', 'aperture', 'footage', 'layer-stack', 'shader-sculpture']
    engine: Literal['pillow', 'browser', 'blender', 'ffmpeg']
    params: SceneParams
    camera: NotRequired[CameraConfig]
    transition: NotRequired[TransitionConfig]
    locked_regions: NotRequired[list[list[int]]]


class AudioCue(TypedDict):
    frame: int
    frequency: int
    duration_frames: int
    instrument: NotRequired[Literal['sine', 'sub_impact', 'harmonic_pluck', 'warm_pad', 'whoosh', 'click_transient']]
    pan: NotRequired[float]
    gain_offset_db: NotRequired[float]


class AudioSettings(TypedDict):
    enabled: bool
    gain_db: float
    cues: list[AudioCue]
    export_stems: NotRequired[bool]
    tracks: NotRequired[list[dict]]


class Constraints(TypedDict, total=False):
    no_text: bool
    no_audio: bool
    no_voice: bool
    no_music: bool
    camera_locked: bool
    offline: bool
    no_paid_services: bool


class QualitySettings(TypedDict, total=False):
    exceptions: dict[str, list[list[int]]]


class Project(TypedDict):
    schema_version: Literal[1]
    id: str
    seed: int
    output: OutputSettings
    scenes: list[Scene]
    audio: AudioSettings
    camera: NotRequired[CameraConfig]
    constraints: NotRequired[Constraints]
    quality: NotRequired[QualitySettings]


class ProjectMetadata(TypedDict):
    scene_count: int
    frames: int
    fps: str
    duration: str
    plan_sha256: str


class RoutingTask(TypedDict):
    intent: str
    language: NotRequired[str]
    stage: NotRequired[Literal['plan', 'ingest', 'build', 'edit', 'render', 'review', 'export', 'operate']]
    assets: NotRequired[list[str]]
    constraints: NotRequired[Constraints]
    capabilities: NotRequired[list[str]]
    preferred_engines: NotRequired[list[str]]
    include: NotRequired[list[str]]
    exclude: NotRequired[list[str]]
    categories: NotRequired[list[str]]
    max_skills: NotRequired[int]
    context_budget: NotRequired[int]
    word_budget: NotRequired[int]
