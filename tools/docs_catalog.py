from pathlib import Path
from mkdocs.structure.files import File


def on_files(files, config):
    catalog = Path(__file__).resolve().parents[1] / 'ReelSyntax_Skills/CATALOG.md'
    source = catalog.read_text(encoding='utf-8').replace(
        '](library/', '](https://github.com/Remirdy/ReelSyntax/blob/v0.1.0/ReelSyntax_Skills/library/'
    )
    files.append(File.generated(config, 'catalog.md', content=source))
    return files


def on_page_markdown(markdown, **kwargs):
    return markdown.replace('../ReelSyntax_Skills/CATALOG.md', 'catalog.md').replace(
        '../ReelSyntax_Skills/QUALITY_STANDARD.md',
        'https://github.com/Remirdy/ReelSyntax/blob/v0.1.0/ReelSyntax_Skills/QUALITY_STANDARD.md',
    )
