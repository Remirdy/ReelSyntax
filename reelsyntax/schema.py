from typing import Literal, get_args, get_origin, get_type_hints, is_typeddict

from .contracts import Project
from .project import CAMERA_PRESETS, ENGINES, RECIPES, TRANSITIONS
from .shapes import COLOR, SHAPES, shape_schema

REEL_V1_SCHEMA_URL = 'https://remirdy.github.io/ReelSyntax/schemas/reel.v1.schema.json'
CONFIG_V1_SCHEMA_URL = 'https://remirdy.github.io/ReelSyntax/schemas/config.v1.schema.json'
SUPPORTED_SCHEMA_VERSIONS = (1,)


def object_schema(properties, required=()):
    return {
        'type': 'object',
        'properties': properties,
        'required': list(required),
        'additionalProperties': False,
    }


def project_schema():
    definitions = {}

    def describe(annotation):
        origin = get_origin(annotation)
        if is_typeddict(annotation):
            name = annotation.__name__
            definitions[name] = object_schema(
                {k: describe(v) for k, v in get_type_hints(annotation).items()},
                sorted(annotation.__required_keys__),
            )
            return {'$ref': '#/$defs/' + name}
        if origin is Literal:
            return {'enum': list(get_args(annotation))}
        if origin is list:
            return {'type': 'array', 'items': describe(get_args(annotation)[0])}
        if origin is dict:
            from typing import Any

            value = get_args(annotation)[1]
            return {'type': 'object', 'additionalProperties': True if value is Any else describe(value)}
        return {
            'type': {int: 'integer', str: 'string', bool: 'boolean', float: 'number', dict: 'object'}[
                annotation
            ]
        }

    root = describe(Project)
    project = definitions['Project']['properties']
    project['$schema'] = {'type': 'string'}
    project['seed'].update(minimum=0, maximum=2**32 - 1)
    project['scenes'].update(minItems=1, maxItems=1000)
    scene = definitions['Scene']['properties']
    scene['recipe'] = {'enum': sorted(RECIPES)}
    scene['engine'] = {'enum': sorted(ENGINES)}
    scene['id'] = project['id'] = {'type': 'string', 'pattern': '^[a-z0-9]+(-[a-z0-9]+)*$', 'maxLength': 64}
    scene['duration_frames'].update(minimum=1, maximum=10000000)
    definitions['CameraConfig']['properties']['preset'] = {'enum': sorted(CAMERA_PRESETS)}
    definitions['TransitionConfig']['required'] = ['type']
    definitions['TransitionConfig']['properties']['type'] = {'enum': sorted(TRANSITIONS)}
    output = definitions['OutputSettings']['properties']
    for dimension in ('width', 'height'):
        output[dimension].update(minimum=64, maximum=7680, multipleOf=2)
    output['fps']['pattern'] = '^[1-9][0-9]*/[1-9][0-9]*$'
    params = definitions['SceneParams']['properties']
    for key in ('heading', 'subheading', 'kicker'):
        params[key]['maxLength'] = 120
    for key in ('background', 'foreground', 'accent'):
        params[key] = COLOR
    params['shapes'] = {
        'type': 'array',
        'minItems': 1,
        'maxItems': 128,
        'items': {'oneOf': [shape_schema(k) for k in SHAPES]},
    }
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': REEL_V1_SCHEMA_URL,
        'title': 'ReelSyntax project',
        **root,
        '$defs': definitions,
    }


def config_schema():
    from .config import LANG_TAG_RE, PROFILE_NAMES, PROVIDER_NAMES

    lang_prop = {
        'type': 'string',
        'anyOf': [
            {'const': 'auto'},
            {'pattern': LANG_TAG_RE.pattern},
        ],
    }
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': CONFIG_V1_SCHEMA_URL,
        'title': 'ReelSyntax configuration',
        **object_schema(
            {
                'config_version': {'const': 1},
                'general': object_schema(
                    {
                        'ui_lang': lang_prop,
                        'video_lang': lang_prop,
                        'allow_network': {'type': 'boolean'},
                        'attribution': {'type': 'boolean'},
                    }
                ),
                'provider': object_schema(
                    {
                        'name': {'enum': sorted(PROVIDER_NAMES)},
                        'model': {'type': 'string', 'maxLength': 128},
                        'endpoint': {'type': 'string', 'maxLength': 512},
                        'timeout_sec': {'type': 'integer', 'minimum': 1, 'maximum': 600},
                        'max_repairs': {'type': 'integer', 'minimum': 0, 'maximum': 3},
                    }
                ),
                'paths': object_schema(
                    {
                        'ffmpeg': {'type': 'string'},
                        'ffprobe': {'type': 'string'},
                        'blender': {'type': 'string'},
                    }
                ),
                'render': object_schema(
                    {
                        'default_profile': {'enum': sorted(PROFILE_NAMES)},
                        'cache_budget_mib': {'type': 'integer', 'minimum': 0, 'maximum': 1_048_576},
                        'reduced_motion': {'type': 'boolean'},
                        'timeout_sec': {'type': 'integer', 'minimum': 1, 'maximum': 3600},
                    }
                ),
            }
        ),
    }


def schema_for(kind: str = 'reel', schema_version: int = 1) -> dict:
    if type(schema_version) is not int or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f'Unsupported schema version {schema_version}; supported versions: {list(SUPPORTED_SCHEMA_VERSIONS)}')
    if kind == 'reel':
        return project_schema()
    if kind == 'config':
        return config_schema()
    if kind == 'format':
        from .formats.schema import format_schema

        return format_schema()
    raise ValueError(f'Unknown schema kind: {kind}')
