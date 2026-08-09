# Am I Being Carried? - Rocket League Stats Tracker

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.1-purple.svg)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-APACHE-yellow.svg)](LICENSE)

A web application that analyzes Rocket League competitive match data to determine if players are being carried by their teammates. Built with Flask and Bootstrap, featuring real-time stats tracking and a unique "carried score" algorithm.

## Features

- **Player Search**: Search any Rocket League player by username and platform
- **Recent Matches**: Display last 10 competitive matches (1v1, 2v2, 3v3)
- **Performance Metrics**: Track goals, assists, saves, shots, MVPs, and more
- **Carried Score Algorithm**: AI-powered analysis to detect if you're being carried
  - Win rate analysis
  - MVP rate tracking
  - Performance metrics evaluation
  - 0-100% carried score with descriptive labels
- **Data Caching**: Rate-limited API calls with cached results
- **Share Results**: Generate shareable images with your carried score
- **Responsive Design**: Works on desktop and mobile devices
- **Rate Limiting**: 1 request per 5 minutes to prevent abuse

## Screenshots

### Homepage
![Homepage](screenshots/homepage.png)

### Results Page
![Results Page](screenshots/results.png)

### Carried Score Card
![Carried Score](screenshots/carried-score.png)

## Tech Stack

- **Backend**: Flask (Python 3.8+)
- **Frontend**: Bootstrap 5, Font Awesome 6
- **Database**: PostgreSQL (for production) / SQLite (development)
- **Caching**: Flask session-based caching
- **Rate Limiting**: Flask-Limiter
- **Image Generation**: html2canvas
- **API**: Rocket League Tracker Network API

## Prerequisites

- Python 3.8 or higher
- PostgreSQL (production) or SQLite (development)
- Rocket League Tracker Network API key
- Virtual environment (recommended)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/am-i-being-carried.git
cd am-i-being-carried
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r dependencies.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DEBUG=True

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/amibeingcarried
# Or for SQLite:
# DATABASE_URL=sqlite:///app.db

# Rocket League Tracker API
TRACKER_API_KEY=your-tracker-api-key-here

# Rate Limiting
RATE_LIMIT=1 per 5 minutes
```

### 5. Initialize Database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Run the Application
```bash
flask run
# Or for development with auto-reload:
python app.py
```

Visit `http://localhost:5000` to start using the app!

## Project Structure

```
am-i-being-carried/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── README.md              # This file
├── templates/
│   ├── layout.html        # Base template
│   ├── index.html         # Homepage
│   └── results.html       # Results page
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/
│       └── script.js      # JavaScript functions
├── migrations/            # Database migrations
└── screenshots/           # Screenshots for README
```

## Supported Platforms

- Epic Games (epic)
- Steam (steam)
- PlayStation Network (psn)
- Xbox (xbox)

## Carried Score Algorithm

The carried score algorithm analyzes multiple metrics to determine if a player is being carried:

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Win Rate | 0-40 points | High win rate with low performance = suspicious |
| MVP Rate | 0-25 points | Low MVP rate with high wins = carried |
| Goals/Match | 0-15 points | Low goals = less contribution |
| Saves/Match | 0-10 points | Low saves = weak defense |
| Shot Accuracy | 0-10 points | Low accuracy = poor mechanics |
| Shots/Match | 0-10 points | Low shots = not trying to score |
| Assists/Match | 0-5 points | Low assists = not helping teammates |
| Performance Index | -10 to +5 | Adjusts for exceptional cases |

### Score Categories

| Score Range | Label | Description |
|-------------|-------|-------------|
| 80-100% | Heavy Carry | Significantly carried by teammates |
| 60-79% | Sometimes Carried | Carried in some games |
| 40-59% | Balanced | Contributing fairly to wins |
| 20-39% | Contributor | Pulling your weight |
| 0-19% | Carrying Others | Carrying your team |

## API Endpoints

### GET /
Homepage - Search form

### POST /api/query
Query player data from Tracker Network API
```json
{
  "platform_id": "epic",
  "username": "player_name",
  "force_refresh": true
}
```

### GET /results
Display player results page

### POST /api/refresh
Refresh cached data
```json
{
  "platform_id": "epic",
  "username": "player_name"
}
```

### POST /api/clear_session
Clear session data

## Rate Limiting

- **Limit**: 1 request per 5 minutes (per IP)
- **Cache**: Results cached for 7 days
- **Headers**: `Retry-After` included in rate limit responses

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
# Format code
black app.py models.py

# Check linting
flake8 app.py models.py
```

### Database Management
```bash
# Create a migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Rocket League Tracker Network](https://tracker.gg/rocket-league) for API access
- [Flask-Limiter](https://flask-limiter.readthedocs.io/) for rate limiting
- [html2canvas](https://html2canvas.hertzen.com/) for image generation
- [Bootstrap](https://getbootstrap.com/) for responsive design

## Contact

- GitHub: [@yourusername](https://github.com/yourusername)
- Twitter: [@yourtwitter](https://twitter.com/yourtwitter)
- Email: your.email@example.com

## Links

- [Live Demo](https://amibeingcarried.com)
- [Documentation](https://docs.amibeingcarried.com)
- [Issue Tracker](https://github.com/yourusername/am-i-being-carried/issues)

---

**Made with <3 for the Rocket League Community**

### Star this repo if you find it helpful!