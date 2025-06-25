notnhg # Automated Trading Bot Platform

A comprehensive automated trading bot platform supporting multiple cryptocurrency exchanges with strategy backtesting, user management, and performance tracking.

## 🚀 Features

- **Multi-Exchange Support**: Binance, Gate.io, KuCoin, BingX, Bitget
- **Spot & Futures Trading**: Unified interface for both trading types
- **Strategy Framework**: Customizable trading strategies with optimization
- **Backtesting Engine**: Historical strategy validation and performance analysis
- **User Portal**: Subscription management, API key integration, performance tracking
- **Financial Operations**: Deposit/withdrawal request system

## 🏗 Architecture

```
├── backend/                 # FastAPI backend services
│   ├── app/
│   │   ├── api/            # API routes and endpoints
│   │   ├── core/           # Core configuration and utilities
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic services
│   │   ├── trading/        # Trading engine and strategies
│   │   └── utils/          # Utility functions
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Next.js pages
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API service functions
│   │   └── utils/          # Frontend utilities
│   ├── public/             # Static assets
│   └── package.json        # Node.js dependencies
├── docker/                 # Docker configuration files
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## 🛠 Tech Stack

### Backend
- **FastAPI** - High-performance API framework
- **SQLAlchemy** - ORM for database operations
- **Celery** - Asynchronous task processing
- **PostgreSQL** - Primary database
- **Redis** - Caching and session storage
- **RabbitMQ** - Message queuing

### Frontend
- **Next.js** - React framework with SSR
- **Tailwind CSS** - Styling framework
- **Chart.js** - Data visualization
- **TypeScript** - Type safety

### Trading & Analysis
- **ccxt** - Exchange API library
- **pandas** - Data manipulation
- **numpy** - Numerical computing
- **scikit-learn** - Machine learning

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL
- Redis

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd automated-trading-bot
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup**
```bash
cd frontend
npm install
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Database Setup**
```bash
# Using Docker Compose
docker-compose up -d postgres redis rabbitmq
```

6. **Run the Application**
```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

## 📁 Project Structure Details

### Backend Structure
- **`app/api/`** - REST API endpoints organized by feature
- **`app/core/`** - Configuration, security, and core utilities
- **`app/models/`** - Database models and schemas
- **`app/services/`** - Business logic and external service integrations
- **`app/trading/`** - Trading engine, strategies, and exchange connectors
- **`app/utils/`** - Helper functions and utilities

### Frontend Structure
- **`src/components/`** - Reusable React components
- **`src/pages/`** - Next.js pages and routing
- **`src/hooks/`** - Custom React hooks
- **`src/services/`** - API integration and external services
- **`src/utils/`** - Frontend utilities and helpers

## 🔧 Configuration

The application uses environment variables for configuration. See `.env.example` for all available options.

Key configuration areas:
- Database connections
- Exchange API credentials
- Redis and RabbitMQ settings
- JWT secrets
- External service API keys

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Documentation

- [API Documentation](./docs/api.md)
- [Trading Strategy Guide](./docs/strategies.md)
- [Deployment Guide](./docs/deployment.md)
- [Contributing Guidelines](./docs/contributing.md)

## 🤝 Contributing

Please read [CONTRIBUTING.md](./docs/contributing.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 