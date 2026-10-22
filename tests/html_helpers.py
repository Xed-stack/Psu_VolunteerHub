"""Small semantic HTML queries for server-rendered regression checks."""
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    @property
    def text(self):
        return ' '.join(''.join(child.text if isinstance(child, Element) else child
                                for child in self.children).split())

    def all(self, tag, **attrs):
        matches = []
        for child in self.children:
            if isinstance(child, Element):
                if child.tag == tag and all(child.attrs.get(key) == value for key, value in attrs.items()):
                    matches.append(child)
                matches.extend(child.all(tag, **attrs))
        return matches

    def one(self, tag, **attrs):
        matches = self.all(tag, **attrs)
        assert len(matches) == 1, f'Expected one {tag} {attrs}, found {len(matches)}'
        return matches[0]


class _Parser(HTMLParser):
    VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element('document')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(markup):
    parser = _Parser()
    parser.feed(markup)
    parser.close()
    return parser.root


def form_with_control(document, name, tags=('input', 'select', 'textarea')):
    forms = [form for form in document.all('form')
             if any(form.all(tag, name=name) for tag in tags)]
    assert len(forms) == 1, f'Expected one form containing {name}, found {len(forms)}'
    return forms[0]


def form_values(form):
    values = {}
    for tag in ('input', 'select', 'textarea'):
        for control in form.all(tag):
            name = control.attrs.get('name')
            kind = control.attrs.get('type', 'text')
            if not name or 'disabled' in control.attrs or kind in ('submit', 'button', 'reset'):
                continue
            if kind in ('checkbox', 'radio') and 'checked' not in control.attrs:
                continue
            if tag == 'select':
                options = control.all('option')
                selected = [option for option in options if 'selected' in option.attrs]
                if not selected and 'multiple' not in control.attrs:
                    selected = options[:1]
                entries = [option.attrs.get('value', option.text) for option in selected]
            else:
                entries = [control.text if tag == 'textarea' else control.attrs.get('value', '')]
            values.setdefault(name, []).extend(entries)
    return values
