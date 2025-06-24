# Simple TDS

This project is a lightweight traffic distribution system (TDS) written in Python using Flask. It redirects visitors to different URLs depending on their country and device type.

## Features

- Detects visitor country using **ip-api.com**
- Determines device type (mobile/desktop) from the User-Agent header
- Redirects according to rules in `routes.json`

## Installation

1. Install Python 3.8 or later.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python tds.py
```

By default the server listens on `http://0.0.0.0:8000/`.

### Configuration

Edit `routes.json` to set up your redirect rules. Example:

```json
{
  "US": {
    "mobile": "https://example.com/us-mobile",
    "desktop": "https://example.com/us-desktop"
  },
  "RU": {
    "default": "https://example.ru"
  },
  "default": "https://example.net"
}
```

Keys are ISO country codes. Use `default` to handle unspecified countries or devices. When a visitor from the US on a mobile device opens the TDS link, they will be redirected to `https://example.com/us-mobile`.

## Notes

This simple TDS relies on an external API for geo lookup. If the API is unavailable, the app falls back to the `default` rule.
