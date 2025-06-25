# 🚀 Automated Trading Bot Platform - Setup Guide

## Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose** - For containerized services
- **Python 3.9+** - For backend development (optional)
- **Node.js 18+** - For frontend development (optional)

### Option 1: Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd automated-trading-bot
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup.sh
   ```

3. **Configure your environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

### Option 2: Manual Setup

#### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp ../env.example .env
   # Edit .env with your configuration
   ```

5. **Run the backend**
   ```bash
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run the frontend**
   ```bash
   npm run dev
   ```

#### Database Setup

1. **Start PostgreSQL, Redis, and RabbitMQ**
   ```bash
   docker-compose up -d postgres redis rabbitmq
   ```

2. **Wait for services to be ready**
   ```bash
   sleep 10
   ```

## 🏗 Project Structure

```
automated-trading-bot/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration & utilities
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   ├── trading/        # Trading engine
│   │   └── utils/          # Helper functions
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Next.js pages
│   │   ├── hooks/          # Custom hooks
│   │   ├── services/       # API services
│   │   └── utils/          # Frontend utilities
│   └── package.json        # Node.js dependencies
├── docker-compose.yml      # Docker services
├── scripts/                # Utility scripts
├── data/                   # Data storage
├── uploads/                # File uploads
└── docs/                   # Documentation
```

## 🔧 Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/trading_bot

# Redis
REDIS_URL=redis://localhost:6379/0

# Exchange APIs
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
BINANCE_TESTNET=true

# Security
SECRET_KEY=your-super-secret-key
```

### Exchange API Setup

1. **Binance**
   - Create API key at https://www.binance.com/en/my/settings/api-management
   - Enable spot & futures trading permissions
   - Use testnet for development

2. **Gate.io**
   - Create API key at https://www.gate.io/myaccount/apikeys
   - Enable trading permissions

3. **KuCoin**
   - Create API key at https://www.kucoin.com/account/api
   - Set passphrase and enable trading

4. **BingX**
   - Create API key at https://bingx.com/en-us/support/articles/360015429174
   - Enable trading permissions

5. **Bitget**
   - Create API key at https://www.bitget.com/en/user/settings/api-management
   - Set passphrase and enable trading

## 🚀 Running the Application

### Development Mode

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Mode

```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale celery_worker=3
```

## 📊 Accessing Services

Once running, access the following:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672
- **Redis Commander**: http://localhost:8081 (if enabled)

## 🔍 Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check what's using the port
   lsof -i :8000
   # Kill the process or change port in docker-compose.yml
   ```

2. **Database connection issues**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   # View logs
   docker-compose logs postgres
   ```

3. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod +x scripts/setup.sh
   ```

4. **Memory issues**
   ```bash
   # Increase Docker memory limit
   # In Docker Desktop: Settings > Resources > Memory
   ```

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access container shell
docker-compose exec backend bash
docker-compose exec postgres psql -U trading_user -d trading_bot
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
# Run with Docker
docker-compose exec backend pytest tests/integration/
```

## 📈 Monitoring

### Health Checks

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:3000/api/health
```

### Performance Monitoring

- **Backend**: Built-in FastAPI monitoring
- **Database**: PostgreSQL monitoring queries
- **Queue**: RabbitMQ management interface
- **Cache**: Redis monitoring

## 🔒 Security

### Best Practices

1. **Environment Variables**
   - Never commit `.env` files
   - Use strong, unique secrets
   - Rotate API keys regularly

2. **API Security**
   - Use HTTPS in production
   - Implement rate limiting
   - Validate all inputs

3. **Database Security**
   - Use strong passwords
   - Limit database access
   - Regular backups

4. **Exchange API Security**
   - Use IP whitelisting
   - Minimal required permissions
   - Monitor API usage

## 📚 Next Steps

1. **Configure Exchange APIs**
   - Add your API keys to `.env`
   - Test connections

2. **Create Trading Strategies**
   - Implement your custom strategy
   - Backtest thoroughly

3. **Set Up Monitoring**
   - Configure alerts
   - Monitor performance

4. **Deploy to Production**
   - Set up SSL certificates
   - Configure domain
   - Set up backups

## 🤝 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Create GitHub issues
- **Discussions**: Use GitHub discussions
- **Email**: support@yourdomain.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 