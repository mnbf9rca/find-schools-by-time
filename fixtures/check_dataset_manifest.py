"""Validate a dataset manifest: uv run fixtures/check_dataset_manifest.py MANIFEST.

Self-test: uv run fixtures/check_dataset_manifest.py --check
"""
import argparse
import json
from pathlib import Path


def validate(value, schema=None, path='$') -> list[str]:
    if schema is None:
        schema = json.loads(Path(__file__).with_name('manifest.schema.json').read_text())
    types = {'object': (dict,), 'array': (list,), 'string': (str,),
             'integer': (int,), 'number': (int, float), 'null': (type(None),)}
    if 'type' in schema:
        allowed = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(type(value) in types[kind] for kind in allowed):
            return [f'{path}: expected {schema["type"]}.']
    errors = []
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: expected one of {schema["enum"]!r}.')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}.{key}: required field is missing.')
        for key, item in value.items():
            if key in properties:
                errors.extend(validate(item, properties[key], f'{path}.{key}'))
            elif schema.get('additionalProperties') is False:
                errors.append(f'{path}.{key}: unexpected field.')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            errors.append(f'{path}: expected at least {schema["minItems"]} items.')
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            errors.append(f'{path}: expected at most {schema["maxItems"]} items.')
        for index, item in enumerate(value):
            if 'items' in schema:
                errors.extend(validate(item, schema['items'], f'{path}[{index}]'))
    return errors


def check():
    schema = {'type': 'array', 'minItems': 1, 'maxItems': 1, 'items': {
        'type': 'object', 'required': ['n'], 'additionalProperties': False,
        'properties': {'n': {'type': 'integer', 'enum': [1]}}}}
    assert validate([{'n': 1}], schema) == []
    for value in ([], [{'n': 1}] * 2, [{}], [{'n': True}], [{'n': 2}],
                  [{'n': 1, 'extra': 0}], ['invalid']):
        assert validate(value, schema), value
    assert validate({}), 'An empty dataset manifest must fail.'
    print('ok')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', nargs='?', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
        return 0
    if args.manifest is None:
        parser.error('provide a manifest path or --check')
    try:
        errors = validate(json.loads(args.manifest.read_text()))
    except (OSError, ValueError) as error:
        print(f'Cannot check manifest: {error}')
        return 1
    if errors:
        print('\n'.join(errors))
        return 1
    print('Passed: dataset manifest matches the schema.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
