# Automated Trading Bot Platform

A comprehensive automated trading bot platform supporting multiple cryptocurrency exchanges with advanced dynamic stop loss management, strategy backtesting, user management, and performance tracking.

## 🚀 Features

- **Multi-Exchange Support**: Binance, Gate.io, KuCoin, BingX, Bitget
- **Spot & Futures Trading**: Unified interface for both trading types
- **Advanced Dynamic Stop Loss**: Intelligent stop loss management with cancel-and-replace logic
- **Strategy Framework**: Customizable trading strategies with optimization
- **Backtesting Engine**: Historical strategy validation and performance analysis
- **User Portal**: Subscription management, API key integration, performance tracking
- **Financial Operations**: Deposit/withdrawal request system
- **Real-time Monitoring**: Live trade tracking and performance analytics

## 🆕 Recent Updates

### Dynamic Stop Loss System (Latest)
- ✅ **Cancel-and-Replace Logic**: Prevents duplicate stop loss orders on exchanges
- ✅ **EMA25 Trailing Stop Loss**: Dynamic stop loss updates based on technical indicators
- ✅ **Robust Error Handling**: Timeout management and retry mechanisms
- ✅ **Trading Rule Enforcement**: Validates stop loss prices against market conditions
- ✅ **Multi-Flow Integration**: Works across manual trading, bot trading, and retry scenarios

### Enhanced Features
- 🔄 **Improved Retry Logic**: Robust handling of failed stop loss orders
- 🛡️ **Safe Wrapper Validation**: Prevents invalid stop loss updates
- 📊 **Real-time Position Tracking**: Live monitoring of open positions
- ⚡ **Performance Optimizations**: Faster order processing and response times

## 🏗 Architecture

```
├── backend/                 # FastAPI backend services
│   ├── app/
│   │   ├── api/            # API routes and endpoints
│   │   ├── core/           # Core configuration and utilities
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic services
│   │   │   ├── manual_stop_loss_service.py    # Dynamic stop loss management
│   │   │   ├── stop_loss_timeout_handler.py   # Robust timeout handling
│   │   │   └── bot_service.py                 # Bot management
│   │   ├── trading/        # Trading engine and strategies
│   │   │   ├── exchanges/  # Exchange connectors
│   │   │   └── strategies/ # Trading strategies
│   │   ├── tasks/          # Celery background tasks
│   │   └── utils/          # Utility functions
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js frontend application
│   ├── app/
│   │   ├── components/     # React components
│   │   ├── dashboard/      # Trading dashboard
│   │   ├── contexts/       # React contexts
│   │   └── services/       # API service functions
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
- **ccxt** - Exchange API integration

### Frontend
- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Styling framework
- **Chart.js** - Data visualization
- **TypeScript** - Type safety

### Trading & Analysis
- **ccxt** - Exchange API library
- **pandas** - Data manipulation
- **numpy** - Numerical computing
- **pandas-ta** - Technical analysis indicators

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
# Using Docker Compose (Recommended)
docker-compose up -d

# Or run individually:
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

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
# Run comprehensive dynamic stop loss tests
cd backend
docker-compose exec backend python test_dynamic_stoploss_system.py

# Run forced test with real data
docker-compose exec backend python force_dynamic_stoploss_test.py

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
- [Dynamic Stop Loss Guide](./docs/dynamic_stop_loss.md)
- [Deployment Guide](./docs/deployment.md)
- [Contributing Guidelines](./docs/contributing.md)

## 🎯 Key Features Explained

### Dynamic Stop Loss System
The platform features an advanced dynamic stop loss system that:

- **Prevents Duplicate Orders**: Uses cancel-and-replace logic to ensure only one stop loss order per position
- **EMA25 Trailing**: Automatically updates stop losses based on EMA25 technical indicator
- **Rule Enforcement**: Validates stop loss prices against market conditions and trading rules
- **Robust Error Handling**: Manages timeouts, retries, and edge cases gracefully
- **Multi-Exchange Support**: Works consistently across all supported exchanges

### Trading Strategies
- **Cassava Strategy**: Advanced trend-following strategy with dynamic stop loss
- **Custom Strategies**: Framework for building and testing custom strategies
- **Backtesting**: Comprehensive historical validation of strategies

### User Management
- **Multi-User Support**: Secure user authentication and authorization
- **API Key Management**: Secure storage and management of exchange API keys
- **Performance Tracking**: Real-time monitoring of trading performance

## 🤝 Contributing

Please read [CONTRIBUTING.md](./docs/contributing.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review the test files for usage examples 