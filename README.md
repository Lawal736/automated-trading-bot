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

### Digital Ocean Deployment Ready (Latest)
- ✅ **GitHub Actions CI/CD**: Automatic deployment from GitHub to Digital Ocean
- ✅ **Production Docker Configuration**: Optimized for cloud deployment
- ✅ **SSL/TLS Support**: Secure HTTPS with Let's Encrypt integration
- ✅ **Automated Backups**: Daily database and data backups
- ✅ **Monitoring & Health Checks**: Comprehensive system monitoring
- ✅ **Security Hardening**: Firewall, fail2ban, and security headers

### Dynamic Stop Loss System
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
├── scripts/                # Utility scripts
│   ├── deploy.sh           # Digital Ocean deployment script
│   └── setup-digitalocean.sh # Server setup automation
├── docs/                   # Documentation
└── .github/workflows/      # GitHub Actions CI/CD
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

### DevOps & Deployment
- **Docker & Docker Compose** - Containerization
- **Digital Ocean** - Cloud hosting
- **GitHub Actions** - CI/CD pipeline
- **Nginx** - Reverse proxy and load balancer
- **Let's Encrypt** - SSL certificates

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL
- Redis

### Local Development

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

## 🌐 Digital Ocean Deployment

### Quick Deployment

1. **Set up Digital Ocean resources**
   - Create a Container Registry
   - Create a Droplet (Ubuntu 22.04 LTS, 2GB RAM minimum)
   - Generate API token

2. **Configure GitHub Secrets**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add: `DIGITALOCEAN_ACCESS_TOKEN`, `DIGITALOCEAN_REGISTRY`, `DIGITALOCEAN_HOST`, `DIGITALOCEAN_USERNAME`, `DIGITALOCEAN_SSH_KEY`

3. **Deploy automatically**
   ```bash
   git push origin main
   ```
   The GitHub Actions workflow will automatically build and deploy to Digital Ocean.

### Manual Deployment

For detailed step-by-step instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).

### Server Setup

Run the automated server setup script on your Digital Ocean droplet:
```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/your-repo/main/scripts/setup-digitalocean.sh | sudo bash
```

## 🔧 Configuration

The application uses environment variables for configuration. See `.env.example` for development and `env.prod.example` for production options.

Key configuration areas:
- Database connections
- Exchange API credentials
- Redis and RabbitMQ settings
- JWT secrets
- External service API keys
- Digital Ocean registry settings

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
- **[Digital Ocean Deployment Guide](./DEPLOYMENT_GUIDE.md)** ⭐
- [Contributing Guidelines](./docs/contributing.md)

## 🎯 Key Features Explained

### Digital Ocean Deployment
The platform is fully optimized for Digital Ocean deployment with:
- **Automatic CI/CD**: GitHub Actions workflow for seamless deployment
- **Production Security**: SSL/TLS, firewall, fail2ban, security headers
- **Monitoring**: Health checks, log rotation, automated backups
- **Scalability**: Docker containers with load balancing
- **Cost Optimization**: Efficient resource usage and monitoring

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
- For deployment issues, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) 