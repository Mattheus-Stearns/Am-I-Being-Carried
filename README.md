# 🏆 Am I Being Carried? - Rocket League Stats Tracker

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A web application that analyzes Rocket League competitive match data to determine if you're being carried by your teammates. Upload replays or search any player to get detailed stats and a unique "carried score."

## 🚀 Features

- **🔍 Player Search**: Search any Rocket League player by username and platform (Epic, Steam, PSN, Xbox)
- **📊 Recent Matches**: Display last 10 competitive matches (2v2, 3v3) - 1v1 matches are excluded
- **📈 Performance Metrics**: Track goals, assists, saves, shots, MVPs, and more
- **🎯 Carried Score Algorithm**: AI-powered analysis to detect if you're being carried
  - Win rate analysis
  - MVP rate tracking
  - Performance metrics evaluation
  - 0-100% carried score with descriptive labels
- **🎮 Replay Analysis**: Upload `.replay` files for detailed match analysis
  - Player statistics (goals, assists, saves, shots)
  - Boost usage and efficiency metrics
  - Player speed tracking
  - Event timeline
  - Visual graphs and charts
- **📈 ELO History**: Track rating changes over time (coming soon)
- **🔄 Data Caching**: Rate-limited API calls with cached results
- **📱 Share Results**: Generate shareable images with your carried score
- **🖥️ Responsive Design**: Works on desktop and mobile devices
- **🔒 Rate Limiting**: 1 request per 5 minutes to prevent abuse
- **💬 Feedback System**: Submit feedback directly from the footer
- **❤️ Community Support**: Donation system to help cover API costs

## 📸 Screenshots

### Homepage
![Homepage](screenshots/homepage.png)

### Results Page
![Results Page](screenshots/results.png)

### Carried Score Card
![Carried Score](screenshots/carried-score.png)

### Replay Analysis
![Replay Analysis](screenshots/replay-analysis.png)

## 🛠️ Tech Stack

- **Backend**: Flask 3.0.0 (Python 3.10+)
- **Database**: PostgreSQL 15+ (with SQLAlchemy ORM)
- **Caching**: Redis + Flask-Session (server-side sessions)
- **Rate Limiting**: Flask-Limiter (hybrid IP + session-based)
- **Replay Analysis**: Custom `rrrocket` parser (Rust-based)
  - Telemetry data extraction
  - Boost usage analytics
  - Speed and position tracking
- **Frontend**: Bootstrap 5, Font Awesome 6, Chart.js
- **Image Generation**: html2canvas
- **API Integration**: Parse.bot API (paid credits)
- **Payments**: Stripe (donations)

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL 15+ (production) or SQLite (development)
- Redis (optional, for production)
- Parse.bot API key (for player data)
- Stripe account (for donations)

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/am-i-being-carried.git
cd am-i-being-carried
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/amibeingcarried

# Parse.bot API
API_KEY=pmx_your-api-key-here

# Stripe (optional, for donations)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxx

# Authorized IPs (comma-separated)
AUTHORIZED_IPS=127.0.0.1,98.151.210.183

# Redis (optional, for production)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
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
```

Or with Gunicorn (production):
```bash
gunicorn -w 4 -b 127.0.0.1:9040 app:app
```

Visit `http://localhost:5000` to start using the app!

## 📁 Project Structure

```
am-i-being-carried/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── models.py              # Database models
├── extensions.py          # Flask extensions
├── database.py            # Database initialization
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── README.md              # This file
├── routes/
│   ├── __init__.py        # Blueprint registration
│   ├── main.py            # Main routes (index, results, support)
│   ├── api.py             # API endpoints
│   ├── webhook.py         # Stripe webhook handler
│   ├── admin.py           # Admin routes
│   ├── support.py         # Support/donation routes
│   └── replay.py          # Replay analysis routes
├── services/
│   ├── api_service.py     # Parse.bot API calls
│   ├── cache_service.py   # Caching logic
│   └── suggestion_service.py # "Did you mean?" suggestions
├── utils/
│   ├── helpers.py         # Helper functions
│   ├── validators.py      # Input validation
│   └── season_dates.py    # Rocket League season mapping
├── replay_analyzer/       # Replay parsing and analysis
│   ├── parse.py           # Replay parsing using rrrocket
│   ├── dataframe.py       # Telemetry data extraction
│   └── graph.py           # Graph generation
├── templates/
│   ├── layout.html        # Base template
│   ├── index.html         # Homepage
│   ├── results.html       # Results page
│   ├── history.html       # ELO history
│   ├── donate.html        # Donation page
│   ├── support.html       # Support page
│   ├── upload_replay.html # Replay upload
│   ├── replay_analysis.html # Replay analysis results
│   └── admin/             # Admin templates
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/
│       └── script.js      # JavaScript functions
├── migrations/            # Database migrations
├── uploads/               # Uploaded files
│   ├── replays/           # Temporary replay storage
│   └── analysis/          # Replay analysis output
├── scripts/               # Utility scripts
│   ├── analytics.py       # API usage analytics
│   ├── cleanup.py         # Database cleanup
│   └── populate_suggestions.py # Suggestion population
└── rocket_league_ml/
    ├── data_pipeline/
    │   ├── __init__.py
    │   ├── ballchasing_downloader.py    # Fetch replays from API
    │   ├── replay_processor.py           # Process replays with your parser
    │   ├── feature_extractor.py          # Convert to 1-second snapshots
    │   ├── data_storage.py               # Store/load processed data
    │   └── config.py                     # Configuration
    ├── data/
    │   ├── raw/                          # Downloaded .replay files
    │   ├── processed/                    # Processed DataFrames (Parquet)
    │   └── features/                     # Feature-engineered data for ML
    ├── scripts/
    │   ├── download_replays.py           # CLI to download
    │   ├── process_replays.py            # CLI to process
    │   └── prepare_dataset.py            # Prepare final dataset
    └── requirements_data_pipeline.txt    # Additional dependencies
```

## 🎮 Supported Platforms

- Epic Games (epic)
- Steam (steam)
- PlayStation Network (psn)
- Xbox (xbox)

## 📊 Carried Score Algorithm

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
| 80-100% | 🚨 Heavy Carry | Significantly carried by teammates |
| 60-79% | ⚠️ Sometimes Carried | Carried in some games |
| 40-59% | ⚖️ Balanced | Contributing fairly to wins |
| 20-39% | 💪 Contributor | Pulling your weight |
| 0-19% | 🏆 Carrying Others | Carrying your team |

## 🎯 Replay Analysis Features

The replay analyzer extracts detailed match data from `.replay` files:

1. **Player Statistics**
   - Goals, assists, saves, shots
   - Score and MVP status
   - Boost usage (average, max, min)
   - Time with boost levels

2. **Visual Graphs**
   - Player speed tracking
   - Boost usage over time
   - Candlestick charts for player activity
   - Combined performance metrics

3. **Telemetry Data**
   - CSV export of all telemetry
   - Position and velocity data
   - Frame-by-frame analysis

## 🚀 API Endpoints

### GET /
Homepage - Search form

### POST /api/query
Query player data from Parse.bot API
```json
{
  "platform_id": "epic",
  "username": "player_name",
  "force_refresh": true
}
```

### GET /results
Display player results page

### POST /replay/upload
Upload and analyze a replay file (multipart/form-data)

### GET /replay/download/<replay_id>/<filename>
Download analysis files (PNG, CSV, TXT)

### POST /api/feedback
Submit feedback
```json
{
  "name": "Optional",
  "email": "optional@example.com",
  "rating": 5,
  "message": "Great app!"
}
```

## 🔐 Rate Limiting

- **Limit**: 1 request per 5 minutes (hybrid IP + session-based)
- **Cache**: Results cached for 24 hours
- **Authorized IPs**: Bypass rate limiting (configured in `.env`)

## 🧪 Development

### Running Tests
```bash
pytest tests/
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

### Running Analytics Scripts
```bash
# View API usage statistics
python run.py analytics stats

# Check database size
python run.py size_alert

# Clean up old data
python run.py cleanup --days 90 --dry-run
```

## 🚀 Deployment

### Deploy to VPS with GitHub Actions

1. Set up GitHub secrets:
   - `SSH_HOST`: Your VPS IP
   - `SSH_USERNAME`: Your VPS username
   - `SSH_PRIVATE_KEY`: Your SSH private key
   - `SECRET_KEY`, `DATABASE_URL`, `API_KEY`: App secrets

2. Push to `main` branch to trigger deployment

### Manual Deployment
```bash
# Pull latest code
git pull origin main

# Install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Apply migrations
flask db upgrade

# Restart service
sudo systemctl restart amibeingcarried
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Parse.bot](https://parse.bot) for API access
- [rrrocket](https://github.com/rrrocket) for replay parsing
- [Flask-Limiter](https://flask-limiter.readthedocs.io/) for rate limiting
- [html2canvas](https://html2canvas.hertzen.com/) for image generation
- [Bootstrap](https://getbootstrap.com/) for responsive design

## 📬 Contact

- GitHub: [@yourusername](https://github.com/yourusername)
- Website: [amibeingcarried.com](https://amibeingcarried.com)

---

**Made with ❤️ for the Rocket League Community**

### ⭐ Star this repo if you find it helpful!