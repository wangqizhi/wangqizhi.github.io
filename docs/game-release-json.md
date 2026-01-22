# Game Release JSON Format

This project loads release data from JSON files located at:

```
public/data/gamerelase/YYYY/MMDD-data.json
```

Each file represents a single release date and can include multiple games.

## File Naming

- `YYYY` is the 4-digit year.
- `MMDD` is the 2-digit month + 2-digit day.
- Example: `public/data/gamerelase/2025/0610-data.json`

## JSON Schema (conceptual)

```
{
  "date": "YYYY-MM-DD",
  "displayDate": "Human friendly date string",
  "games": [
    {
      "title": "Game title",
      "genre": ["Tag", "Tag"],
      "style": "Short description of the game style",
      "studio": "Studio or team name",
      "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"]
    }
  ]
}
```

## Field Rules

Top level
- `date` (string, required): Must be `YYYY-MM-DD`.
- `displayDate` (string, optional): Used for UI display. If omitted, `date` is used.
- `games` (array, required): One or more game objects.

Game object
- `title` (string, required)
- `genre` (string[], required): Short tags like `RPG`, `Action`, `Strategy`.
- `style` (string, required): One sentence describing the game.
- `studio` (string, required)
- `platforms` (string[], required): Use common platform names.

## Example

```
{
  "date": "2025-06-10",
  "displayDate": "Jun 10, 2025",
  "games": [
    {
      "title": "Glass Transit",
      "genre": ["Action", "Platformer"],
      "style": "Momentum-based movement through kinetic cityscapes.",
      "studio": "Bright Circuit",
      "platforms": ["PC"]
    }
  ]
}
```
