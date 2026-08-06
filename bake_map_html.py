"""
Re-bakes cbpc_guest_map.html with the current contents of map_data.json.
Finds the existing "const DATA = {...};" line in the HTML and replaces it
in place -- everything else about the file (styling, layout, interaction
logic) stays untouched.

Usage:
    python3 export_map_data.py      # regenerate map_data.json first
    python3 bake_map_html.py        # then inject it into the HTML
"""
import re
import json

HTML_PATH = "cbpc_guest_map.html"
DATA_PATH = "map_data.json"


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    compact_json = json.dumps(data)

    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(r"const DATA = \{.*?\};", re.DOTALL)
    if not pattern.search(html):
        raise SystemExit("Could not find 'const DATA = {...};' in the HTML -- check the file wasn't restructured.")

    new_html = pattern.sub(lambda m: f"const DATA = {compact_json};", html, count=1)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"Re-baked {HTML_PATH} with {len(data['on_map'])} on-map and {len(data['off_map'])} off-map guests.")


if __name__ == "__main__":
    main()
