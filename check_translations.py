import ast
from pathlib import Path


root = Path('c:/Users/Osana/Documents/1212')
loc = root / 'localization.py'
app_files = [
    root / 'rescue app.py',
    root / 'mobile_rescue_app.py',
]


def literal_translation_keys(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != 't':
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
    return keys


def localized_keys_by_language(path: Path) -> dict[str, set[str]]:
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == 'TRANSLATIONS' for target in node.targets):
            continue
        languages: dict[str, set[str]] = {}
        for language_key, language_node in zip(node.value.keys, node.value.values):
            if not isinstance(language_key, ast.Constant) or not isinstance(language_key.value, str):
                continue
            if not isinstance(language_node, ast.Dict):
                continue
            keys: set[str] = set()
            for key_node in language_node.keys:
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    keys.add(key_node.value)
            languages[language_key.value] = keys
        return languages
    return {}


keys = set()
for app in app_files:
    keys.update(literal_translation_keys(app))

localized_keys = localized_keys_by_language(loc)
missing = {
    language: sorted(keys - language_keys)
    for language, language_keys in localized_keys.items()
    if keys - language_keys
}
print('missing:', missing)
