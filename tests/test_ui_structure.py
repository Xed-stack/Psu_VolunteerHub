"""Structural regression checks for the shared Bare CSS interface."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _templates():
    return list(TEMPLATES.rglob("*.html"))


def test_tailwind_is_not_loaded():
    markup = "\n".join(path.read_text(encoding="utf-8") for path in _templates())
    assert "cdn.tailwindcss.com" not in markup
    assert "tailwind.config" not in markup


def test_templates_inherit_a_shared_layout():
    pages = [path for path in _templates()
             if "layouts" not in path.parts and "partials" not in path.parts]
    for page in pages:
        assert "{% extends" in page.read_text(encoding="utf-8"), page


def test_role_styles_and_local_assets_exist():
    styles = ROOT / "static" / "styles"
    for name in ("base", "volunteer", "coordinator", "director", "admin",
                 "public", "auth"):
        assert (styles / f"{name}.css").is_file()
    assets = ROOT / "static" / "assets"
    assert (assets / "PSU-logo.png").is_file()
    assert (assets / "temp_profile.jpg").is_file()


def test_director_menu_has_no_admin_only_items():
    sidebar = (TEMPLATES / "partials" / "sidebar.html").read_text(encoding="utf-8")
    director = sidebar.split("current_user.role == 'director'", 1)[1].split(
        "current_user.role == 'admin'", 1)[0]
    assert "User Management" not in director
    assert "Settings" not in director
