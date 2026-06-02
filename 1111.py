import re
import html
import urllib.request


def print_secret_message(url):
    with urllib.request.urlopen(url) as response:
        page_html = response.read().decode("utf-8")

    # Convert table cells and rows into line breaks
    text = page_html
    text = re.sub(r"</td>", "\n", text)
    text = re.sub(r"</tr>", "\n", text)

    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    points = []

    # The document format is:
    # x-coordinate
    # Character
    # y-coordinate
    for i in range(len(lines) - 2):
        x_value = lines[i]
        character = lines[i + 1]
        y_value = lines[i + 2]

        if x_value.isdigit() and y_value.isdigit():
            x = int(x_value)
            y = int(y_value)
            points.append((x, y, character))

    if not points:
        return

    max_x = max(x for x, y, character in points)
    max_y = max(y for x, y, character in points)

    grid = [[" " for _ in range(max_x + 1)] for _ in range(max_y + 1)]

    for x, y, character in points:
        grid[y][x] = character

    for row in grid:
        print("".join(row))


# Test with your URL
print_secret_message(
    "https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub"
)