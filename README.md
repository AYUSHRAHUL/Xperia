# Urban Pulse — Smart City Sustainability Ledger

<div align="center">

**Transform local infrastructure problems into measurable sustainability progress aligned with UN SDGs**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)](https://www.mongodb.com/cloud/atlas)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🌟 Overview

Urban Pulse is a comprehensive civic governance platform that transforms hyper-local issue reporting into a live sustainability ledger. Every reported issue is mapped to UN Sustainable Development Goals (SDGs), and the platform quantifies real-world impact including water saved, waste diverted, CO₂ emissions avoided, and community safety improvements.

### ✨ Key Features

#### 🏙️ **Citizen Portal**
- 📍 GPS-based issue reporting with photo uploads
- 📊 Personal impact dashboard showing SDG contributions
- 🎮 Gamification system with points and leaderboards
- 🗺️ Interactive city map showing all reported issues
- 📱 Real-time status tracking across full issue lifecycle

#### 👨‍💼 **Admin Dashboard**
- ✅ Issue verification and validation system
- 👷 Worker assignment and task management
- 📈 Performance analytics and recurring hotspot detection
- ⏱️ Resolution time tracking by category
- 🔍 Comprehensive audit logs for all actions

#### 👷 **Worker Portal**
- 📋 Assigned task management
- 📸 Progress updates with photo documentation
- ✔️ Issue resolution workflow
- 📊 Personal performance metrics

#### 🌍 **Public Transparency**
- 🔴 Live sustainability impact dashboard
- 📊 Monthly trend analysis
- 🏆 Community leaderboard
- 📉 Category-wise resolution analytics

### 🛠️ Tech Stack

- **Backend**: Flask 3.0, PyMongo (MongoDB)
- **Authentication**: JWT access tokens, bcrypt password hashing
- **Database**: MongoDB Atlas (cloud) or local MongoDB
- **Storage**: Cloudinary for image uploads
- **Frontend**: Server-rendered HTML (Jinja2) with Tailwind CSS
- **Maps**: Google Maps API for location features
- **Charts**: Chart.js for data visualization

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- MongoDB (local installation or MongoDB Atlas account)
- Git

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd gajayoti
```

2. **Run the setup script** (Recommended)

```bash
python setup.py
```

This will:
- Check Python version
- Create virtual environment (if needed)
- Create `.env` file from template
- Install dependencies
- Guide you through configuration

**OR** Manual Setup:

3. **Create virtual environment**

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

4. **Install dependencies**

```bash
pip install -r requirements.txt
```

5. **Configure environment variables**

Copy `.env.example` to `.env` and update the values:

```env
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET=your-jwt-secret-here-change-in-production
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=urban_pulse
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

6. **Seed the database** (Optional - creates demo accounts)

```bash
python seed.py
```

This creates three demo accounts:
- **Admin**: `admin@urbanpulse.local` / `admin123`
- **Worker**: `worker@urbanpulse.local` / `worker123`
- **Citizen**: `citizen@urbanpulse.local` / `citizen123`

7. **Run the application**

```bash
python run.py
```

8. **Access the application**

Open your browser and navigate to:
- **Home**: http://localhost:5000/
- **Dashboard**: http://localhost:5000/dashboard
- **Login**: http://localhost:5000/login
- **Register**: http://localhost:5000/register

---

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login user | No |
| GET | `/api/auth/me` | Get current user | Yes |

### Issue Management

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| POST | `/api/issues/create` | Create new issue | Yes | Citizen |
| GET | `/api/issues/all` | Get all issues | Yes | Admin |
| GET | `/api/issues/my` | Get user's issues | Yes | Any |
| GET | `/api/issues/<id>` | Get issue details | Yes | Any |
| GET | `/api/issues/public` | Get public issues (map) | No | - |
| PUT | `/api/issues/verify` | Verify issue | Yes | Admin |
| PUT | `/api/issues/assign` | Assign to worker | Yes | Admin |
| PUT | `/api/issues/update-status` | Update status | Yes | Worker/Admin |
| PUT | `/api/issues/close` | Close issue | Yes | Admin |

### Worker Endpoints

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| GET | `/api/worker/tasks` | Get assigned tasks | Yes | Worker |
| PUT | `/api/worker/update-progress` | Update progress | Yes | Worker |
| PUT | `/api/worker/resolve` | Mark as resolved | Yes | Worker |

### Impact & Analytics

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/impact/global` | Global impact metrics | No |
| GET | `/api/impact/user` | User's impact | Yes |
| GET | `/api/impact/monthly` | Monthly trends | No |
| GET | `/api/impact/leaderboard` | Top users | No |

### Admin Analytics

| Method | Endpoint | Description | Auth Required | Role |
|--------|----------|-------------|---------------|------|
| GET | `/api/admin/department-performance` | Dept performance | Yes | Admin |
| GET | `/api/admin/recurring-issues` | Recurring hotspots | Yes | Admin |
| GET | `/api/admin/resolution-time` | Resolution analytics | Yes | Admin |

### File Upload

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/upload-image` | Upload image to Cloudinary | No |

**Authentication**: Protected routes expect `Authorization: Bearer <token>` header.

---

## 🔄 Issue Lifecycle

Issues flow through the following states:

```
REPORTED → VERIFIED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
```

- **REPORTED**: Citizen submits issue (+10 points, +5 if photo attached)
- **VERIFIED**: Admin validates the issue
- **ASSIGNED**: Admin assigns to worker
- **IN_PROGRESS**: Worker starts working
- **RESOLVED**: Worker marks as complete
- **CLOSED**: Admin closes issue (impact calculated, +20 points to citizen)

Each transition is logged in `audit_logs` with timestamp and actor.

---

## 🌍 Impact Calculation

When an issue reaches **CLOSED** status, the system calculates environmental impact:

### Water Leakage
- Estimated liters saved based on severity and duration

### Garbage Dump
- Waste removed (kg)
- CO₂ reduction from proper waste management

### Potholes & Traffic Issues
- Fuel saved (liters)
- Emissions avoided (kg CO₂)

### Broken Streetlights
- Safety score improvement

All metrics are aggregated in `global_aggregates` collection for the public dashboard.

---

## 🎨 UI/UX Features

- ✨ **Modern Design**: Glassmorphism effects, gradient backgrounds
- 🎭 **Smooth Animations**: Hover effects, transitions, floating elements
- 📱 **Responsive**: Mobile-first design with Tailwind CSS
- 🎨 **Professional Typography**: Inter font family
- 📊 **Data Visualization**: Chart.js for trends and analytics
- 🗺️ **Interactive Maps**: Google Maps integration
- 🔔 **Toast Notifications**: User-friendly feedback
- ⚡ **Real-time Updates**: Auto-refresh every 30 seconds

---

## 🚀 Deployment

### Production Checklist

1. **Environment Variables**
   - Set strong `SECRET_KEY` and `JWT_SECRET`
   - Use MongoDB Atlas for production database
   - Configure Cloudinary for image storage
   - Add Google Maps API key

2. **WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 'app:create_app()'
   ```

3. **Security Headers**
   - Enable HTTPS
   - Configure CORS properly
   - Set secure cookie flags
   - Add rate limiting

4. **Database**
   - Create MongoDB Atlas cluster
   - Set up database indexes
   - Configure backup strategy

5. **Monitoring**
   - Set up error logging
   - Monitor API performance
   - Track user analytics

### Deployment Platforms

- **Heroku**: Use `Procfile` with gunicorn
- **Railway**: Auto-detects Flask apps
- **Render**: Use `render.yaml` configuration
- **DigitalOcean**: Deploy on App Platform or Droplet
- **AWS**: Use Elastic Beanstalk or EC2

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- UN Sustainable Development Goals framework
- Flask and MongoDB communities
- Tailwind CSS for styling
- Chart.js for visualizations
- Google Maps Platform

---

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the development team

---

<div align="center">

**Built with ❤️ for sustainable cities and communities**

</div>
#   X p e r i a  
 