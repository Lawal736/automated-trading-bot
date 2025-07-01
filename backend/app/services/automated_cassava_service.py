"""
Automated Cassava Data Generation Service
Eliminates manual backfill through intelligent gap detection and self-healing
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc, text, or_
from app.models.trading import CassavaTrendData
from app.services.cassava_data_service import CassavaDataService
from app.trading.data_service import data_service
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import List, Dict, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

class AutomatedCassavaService:
    """
    Advanced automated Cassava data generation service with:
    - Intelligent gap detection
    - Robust error handling  
    - Self-healing capabilities
    - Performance optimization
    """

    def __init__(self, db: Session):
        self.db = db
        self.cassava_service = CassavaDataService(db)
        self.trading_pairs = self.cassava_service.get_trading_pairs()
        self.max_workers = 5  # Parallel processing limit
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff delays

    async def run_automated_data_generation(self) -> Dict[str, Any]:
        """
        Main automated data generation process
        """
        start_time = datetime.utcnow()
        logger.info("🤖 Starting automated Cassava data generation")
        
        results = {
            'start_time': start_time,
            'status': 'running',
            'gaps_detected': 0,
            'gaps_filled': 0,
            'errors': 0,
            'total_records_created': 0,
            'total_records_updated': 0,
            'symbols_processed': 0,
            'failed_symbols': [],
            'gap_details': [],
            'performance_metrics': {},
            'health_status': 'unknown'
        }

        try:
            # Step 1: Comprehensive gap analysis
            logger.info("🔍 Step 1: Analyzing data gaps")
            gap_analysis = await self._analyze_all_gaps()
            results['gaps_detected'] = len(gap_analysis['critical_gaps'])
            results['gap_details'] = gap_analysis['gap_summary']
            
            # Step 2: Prioritized gap filling
            logger.info("🔧 Step 2: Filling critical gaps")
            if gap_analysis['critical_gaps']:
                fill_results = await self._fill_gaps_intelligently(gap_analysis['critical_gaps'])
                results.update(fill_results)
            
            # Step 3: Ensure latest data is current
            logger.info("📊 Step 3: Ensuring latest data is current")
            latest_results = await self._ensure_latest_data()
            results['latest_data_status'] = latest_results
            
            # Step 4: Data validation and health check
            logger.info("✅ Step 4: Validating data integrity")
            health_results = await self._validate_data_health()
            results['health_status'] = health_results['status']
            results['validation_details'] = health_results
            
            # Step 5: Performance optimization
            logger.info("🚀 Step 5: Performance optimization")
            optimization_results = await self._optimize_data_storage()
            results['optimization'] = optimization_results
            
            # Final summary
            end_time = datetime.utcnow()
            results['end_time'] = end_time
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            results['status'] = 'completed'
            
            logger.info(f"✅ Automated Cassava data generation completed in {results['duration_seconds']:.2f}s")
            logger.info(f"📈 Summary: {results['gaps_filled']} gaps filled, {results['total_records_created']} records created")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in automated data generation: {e}")
            results['status'] = 'failed'
            results['error'] = str(e)
            results['end_time'] = datetime.utcnow()
            return results

    async def _analyze_all_gaps(self) -> Dict[str, Any]:
        """
        Comprehensive gap analysis across all symbols and date ranges
        """
        logger.info("🔍 Analyzing data gaps across all symbols")
        
        # Expected date range (last 50 days)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today - timedelta(days=49)  # 50 days total including today
        
        # Get actual data range
        date_range_query = self.db.query(
            func.min(CassavaTrendData.date).label('min_date'),
            func.max(CassavaTrendData.date).label('max_date'),
            func.count(CassavaTrendData.id).label('total_records')
        ).first()
        
        analysis = {
            'expected_range': {'start': start_date, 'end': today},
            'actual_range': {
                'start': date_range_query.min_date,
                'end': date_range_query.max_date,
                'total_records': date_range_query.total_records
            },
            'expected_total_records': len(self.trading_pairs) * 50,
            'critical_gaps': [],
            'symbol_gaps': {},
            'date_gaps': [],
            'gap_summary': {}
        }
        
        # Check for missing dates
        missing_dates = await self._find_missing_dates(start_date, today)
        analysis['date_gaps'] = missing_dates
        
        # Check gaps per symbol
        for symbol in self.trading_pairs:
            symbol_gaps = await self._find_symbol_gaps(symbol, start_date, today)
            if symbol_gaps:
                analysis['symbol_gaps'][symbol] = symbol_gaps
                
                # Mark as critical if missing recent data (last 7 days)
                recent_cutoff = today - timedelta(days=7)
                critical_gaps = [gap for gap in symbol_gaps if gap >= recent_cutoff]
                if critical_gaps:
                    analysis['critical_gaps'].extend([
                        {'symbol': symbol, 'date': gap, 'priority': 'high'}
                        for gap in critical_gaps
                    ])
        
        # Generate summary
        analysis['gap_summary'] = {
            'total_missing_dates': len(missing_dates),
            'symbols_with_gaps': len(analysis['symbol_gaps']),
            'critical_gaps_count': len(analysis['critical_gaps']),
            'data_completeness_percent': (
                (analysis['actual_range']['total_records'] / analysis['expected_total_records']) * 100
                if analysis['expected_total_records'] > 0 else 0
            )
        }
        
        logger.info(f"📊 Gap analysis complete: {analysis['gap_summary']}")
        return analysis

    async def _find_missing_dates(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Find dates with missing data"""
        # Get all dates that have at least one record
        existing_dates = self.db.query(CassavaTrendData.date).distinct().all()
        existing_date_set = {d[0].date() for d in existing_dates}
        
        # Generate expected date range
        missing_dates = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.date() not in existing_date_set:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)
        
        return missing_dates

    async def _find_symbol_gaps(self, symbol: str, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Find missing dates for a specific symbol"""
        # Get existing dates for this symbol
        existing_dates = self.db.query(CassavaTrendData.date).filter(
            CassavaTrendData.symbol == symbol
        ).all()
        existing_date_set = {d[0].date() for d in existing_dates}
        
        # Find gaps
        gaps = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.date() not in existing_date_set:
                gaps.append(current_date)
            current_date += timedelta(days=1)
        
        return gaps

    async def _fill_gaps_intelligently(self, critical_gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fill gaps using intelligent prioritization and parallel processing
        """
        logger.info(f"🔧 Filling {len(critical_gaps)} critical gaps")
        
        results = {
            'total_gaps': len(critical_gaps),
            'gaps_filled': 0,
            'gaps_failed': 0,
            'records_created': 0,
            'records_updated': 0,
            'failed_gaps': [],
            'processing_time_seconds': 0
        }
        
        start_time = time.time()
        
        # Group gaps by date for efficient processing
        gaps_by_date = {}
        for gap in critical_gaps:
            date = gap['date']
            if date not in gaps_by_date:
                gaps_by_date[date] = []
            gaps_by_date[date].append(gap['symbol'])
        
        # Process each date
        for date, symbols in gaps_by_date.items():
            try:
                logger.info(f"📅 Processing {len(symbols)} symbols for {date.date()}")
                date_results = await self._process_date_with_retry(date, symbols)
                
                results['records_created'] += date_results['created']
                results['records_updated'] += date_results['updated']
                results['gaps_filled'] += date_results['success_count']
                results['gaps_failed'] += date_results['failed_count']
                
                if date_results['failed_symbols']:
                    results['failed_gaps'].extend([
                        {'date': date, 'symbol': symbol, 'error': 'Failed after retries'}
                        for symbol in date_results['failed_symbols']
                    ])
                
            except Exception as e:
                logger.error(f"❌ Error processing date {date}: {e}")
                results['gaps_failed'] += len(symbols)
                results['failed_gaps'].extend([
                    {'date': date, 'symbol': symbol, 'error': str(e)}
                    for symbol in symbols
                ])
        
        results['processing_time_seconds'] = time.time() - start_time
        logger.info(f"✅ Gap filling completed: {results['gaps_filled']} filled, {results['gaps_failed']} failed")
        
        return results

    async def _process_date_with_retry(self, date: datetime, symbols: List[str]) -> Dict[str, Any]:
        """Process all symbols for a specific date with retry logic"""
        results = {
            'date': date,
            'total_symbols': len(symbols),
            'success_count': 0,
            'failed_count': 0,
            'created': 0,
            'updated': 0,
            'failed_symbols': []
        }
        
        # Process symbols in parallel with limited concurrency
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(self._process_symbol_with_retry, symbol, date): symbol
                for symbol in symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    symbol_result = future.result()
                    if symbol_result['success']:
                        results['success_count'] += 1
                        if symbol_result['action'] == 'created':
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    else:
                        results['failed_count'] += 1
                        results['failed_symbols'].append(symbol)
                        
                except Exception as e:
                    logger.error(f"❌ Exception processing {symbol} for {date}: {e}")
                    results['failed_count'] += 1
                    results['failed_symbols'].append(symbol)
        
        # Commit all changes for this date
        try:
            self.db.commit()
            logger.info(f"✅ Committed data for {date.date()}: {results['success_count']} symbols")
        except Exception as e:
            logger.error(f"❌ Error committing data for {date}: {e}")
            self.db.rollback()
            # Mark all as failed
            results['failed_count'] = results['total_symbols']
            results['success_count'] = 0
            results['failed_symbols'] = symbols
        
        return results

    def _process_symbol_with_retry(self, symbol: str, date: datetime) -> Dict[str, Any]:
        """Process a single symbol with exponential backoff retry"""
        for attempt, delay in enumerate(self.retry_delays):
            try:
                # Check if data already exists
                existing_data = self.db.query(CassavaTrendData).filter(
                    and_(
                        CassavaTrendData.date == date,
                        CassavaTrendData.symbol == symbol
                    )
                ).first()
                
                # Calculate new data
                cassava_data = self.cassava_service.calculate_daily_cassava_data(symbol, date)
                
                if not cassava_data:
                    logger.warning(f"⚠️ No data calculated for {symbol} on {date.date()}")
                    continue  # Retry
                
                if existing_data:
                    # Update existing record
                    existing_data.ema_10 = cassava_data.ema_10
                    existing_data.ema_8 = cassava_data.ema_8
                    existing_data.ema_20 = cassava_data.ema_20
                    existing_data.ema_15 = cassava_data.ema_15
                    existing_data.ema_25 = cassava_data.ema_25
                    existing_data.ema_5 = cassava_data.ema_5
                    existing_data.di_plus = cassava_data.di_plus
                    existing_data.top_fractal = cassava_data.top_fractal
                    existing_data.trading_condition = cassava_data.trading_condition
                    existing_data.price = cassava_data.price
                    existing_data.updated_at = datetime.utcnow()
                    
                    return {'success': True, 'action': 'updated', 'symbol': symbol, 'date': date}
                else:
                    # Create new record
                    self.db.add(cassava_data)
                    return {'success': True, 'action': 'created', 'symbol': symbol, 'date': date}
                
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed for {symbol} on {date.date()}: {e}")
                if attempt < len(self.retry_delays) - 1:
                    time.sleep(delay)
                else:
                    logger.error(f"❌ All retries failed for {symbol} on {date.date()}")
                    return {'success': False, 'symbol': symbol, 'date': date, 'error': str(e)}
        
        return {'success': False, 'symbol': symbol, 'date': date, 'error': 'Max retries exceeded'}

    async def _ensure_latest_data(self) -> Dict[str, Any]:
        """Ensure we have the most recent data available"""
        logger.info("📊 Ensuring latest data is current")
        
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # Check what's the latest date we have data for
        latest_date = self.db.query(func.max(CassavaTrendData.date)).scalar()
        
        results = {
            'expected_latest': yesterday,
            'actual_latest': latest_date,
            'is_current': False,
            'missing_days': 0,
            'action_taken': 'none'
        }
        
        if latest_date:
            latest_date_only = latest_date.date() if hasattr(latest_date, 'date') else latest_date
            yesterday_only = yesterday.date()
            
            if latest_date_only >= yesterday_only:
                results['is_current'] = True
                logger.info("✅ Latest data is current")
            else:
                # Calculate missing days
                missing_days = (yesterday_only - latest_date_only).days
                results['missing_days'] = missing_days
                
                logger.info(f"⚠️ Missing {missing_days} days of recent data")
                
                # Fill the gap
                if missing_days <= 7:  # Only auto-fill if gap is reasonable
                    fill_start = latest_date + timedelta(days=1)
                    await self._fill_date_range(fill_start, yesterday)
                    results['action_taken'] = f'filled_{missing_days}_days'
                else:
                    results['action_taken'] = 'gap_too_large_manual_intervention_needed'
        else:
            logger.warning("⚠️ No data found in database")
            results['action_taken'] = 'no_data_found'
        
        return results

    async def _fill_date_range(self, start_date: datetime, end_date: datetime):
        """Fill a continuous date range"""
        current_date = start_date
        while current_date <= end_date:
            logger.info(f"📅 Filling data for {current_date.date()}")
            
            # Process all symbols for this date
            await self._process_date_with_retry(current_date, self.trading_pairs)
            
            current_date += timedelta(days=1)

    async def _validate_data_health(self) -> Dict[str, Any]:
        """Comprehensive data validation and health check"""
        logger.info("✅ Validating data integrity")
        
        health_results = {
            'status': 'healthy',
            'issues': [],
            'recommendations': [],
            'metrics': {}
        }
        
        try:
            # Check 1: Record counts per symbol
            counts = self.cassava_service.get_records_count_per_symbol()
            expected_count = 50
            
            symbols_with_issues = []
            for symbol, count in counts.items():
                if count != expected_count:
                    symbols_with_issues.append({'symbol': symbol, 'count': count, 'expected': expected_count})
            
            if symbols_with_issues:
                health_results['issues'].append({
                    'type': 'record_count_mismatch',
                    'details': symbols_with_issues
                })
                health_results['recommendations'].append('Run gap filling to normalize record counts')
            
            # Check 2: Date continuity
            date_gaps = await self._check_date_continuity()
            if date_gaps:
                health_results['issues'].append({
                    'type': 'date_continuity_gaps',
                    'details': date_gaps
                })
                health_results['recommendations'].append('Fill date gaps to ensure continuity')
            
            # Check 3: Data quality (null values, outliers)
            quality_issues = await self._check_data_quality()
            if quality_issues:
                health_results['issues'].append({
                    'type': 'data_quality',
                    'details': quality_issues
                })
                health_results['recommendations'].append('Review and clean data quality issues')
            
            # Overall health status
            if health_results['issues']:
                health_results['status'] = 'needs_attention' if len(health_results['issues']) <= 2 else 'unhealthy'
            
            # Calculate metrics
            health_results['metrics'] = {
                'total_symbols': len(self.trading_pairs),
                'symbols_with_data': len(counts),
                'total_records': sum(counts.values()),
                'average_records_per_symbol': sum(counts.values()) / len(counts) if counts else 0,
                'data_completeness_percent': (len([c for c in counts.values() if c == expected_count]) / len(self.trading_pairs)) * 100
            }
            
            logger.info(f"📊 Health check complete: {health_results['status']}")
            return health_results
            
        except Exception as e:
            logger.error(f"❌ Error in health validation: {e}")
            health_results['status'] = 'error'
            health_results['error'] = str(e)
            return health_results

    async def _check_date_continuity(self) -> List[Dict[str, Any]]:
        """Check for gaps in date continuity"""
        # Get min and max dates
        date_range = self.db.query(
            func.min(CassavaTrendData.date),
            func.max(CassavaTrendData.date)
        ).first()
        
        if not date_range[0] or not date_range[1]:
            return []
        
        # Get all unique dates
        existing_dates = self.db.query(CassavaTrendData.date).distinct().order_by(CassavaTrendData.date).all()
        existing_date_set = {d[0].date() for d in existing_dates}
        
        # Check for gaps
        gaps = []
        current_date = date_range[0]
        while current_date <= date_range[1]:
            if current_date.date() not in existing_date_set:
                gaps.append({'date': current_date, 'type': 'missing_date'})
            current_date += timedelta(days=1)
        
        return gaps

    async def _check_data_quality(self) -> List[Dict[str, Any]]:
        """Check for data quality issues"""
        issues = []
        
        try:
            # Check for null values in critical fields
            null_checks = [
                ('ema_10', 'EMA 10'),
                ('ema_25', 'EMA 25'),
                ('trading_condition', 'Trading Condition'),
                ('price', 'Price')
            ]
            
            for field, description in null_checks:
                null_count = self.db.query(CassavaTrendData).filter(
                    getattr(CassavaTrendData, field).is_(None)
                ).count()
                
                if null_count > 0:
                    issues.append({
                        'type': 'null_values',
                        'field': field,
                        'description': description,
                        'count': null_count
                    })
            
            # Check for invalid trading conditions
            valid_conditions = ['BUY', 'SELL', 'SHORT', 'HOLD']
            invalid_conditions = self.db.query(CassavaTrendData).filter(
                ~CassavaTrendData.trading_condition.in_(valid_conditions)
            ).count()
            
            if invalid_conditions > 0:
                issues.append({
                    'type': 'invalid_trading_conditions',
                    'count': invalid_conditions
                })
            
            # Check for unrealistic price values (too high/low)
            unrealistic_prices = self.db.query(CassavaTrendData).filter(
                or_(
                    CassavaTrendData.price < 0.000001,  # Too low
                    CassavaTrendData.price > 1000000    # Too high
                )
            ).count()
            
            if unrealistic_prices > 0:
                issues.append({
                    'type': 'unrealistic_prices',
                    'count': unrealistic_prices
                })
            
        except Exception as e:
            logger.error(f"Error in data quality check: {e}")
            issues.append({
                'type': 'quality_check_error',
                'error': str(e)
            })
        
        return issues

    async def _optimize_data_storage(self) -> Dict[str, Any]:
        """Optimize data storage and cleanup old/redundant data"""
        logger.info("🚀 Optimizing data storage")
        
        results = {
            'cleaned_records': 0,
            'optimized_indexes': False,
            'storage_saved_mb': 0,
            'actions': []
        }
        
        try:
            # Standard cleanup (maintain 50 days per symbol)
            initial_count = self.db.query(CassavaTrendData).count()
            self.cassava_service.cleanup_old_data()
            final_count = self.db.query(CassavaTrendData).count()
            
            results['cleaned_records'] = initial_count - final_count
            if results['cleaned_records'] > 0:
                results['actions'].append(f"Cleaned {results['cleaned_records']} old records")
            
            # Update table statistics (PostgreSQL specific)
            try:
                self.db.execute(text("ANALYZE cassava_trend_data"))
                results['optimized_indexes'] = True
                results['actions'].append("Updated table statistics")
            except Exception as e:
                logger.warning(f"Could not optimize indexes: {e}")
            
            logger.info(f"✅ Storage optimization complete: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in storage optimization: {e}")
            results['error'] = str(e)
            return results

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status for monitoring"""
        try:
            counts = self.cassava_service.get_records_count_per_symbol()
            
            # Get date range
            date_range = self.db.query(
                func.min(CassavaTrendData.date),
                func.max(CassavaTrendData.date)
            ).first()
            
            # Calculate health score
            expected_count = 50
            healthy_symbols = len([c for c in counts.values() if c == expected_count])
            health_score = (healthy_symbols / len(self.trading_pairs)) * 100 if self.trading_pairs else 0
            
            return {
                'timestamp': datetime.utcnow(),
                'total_symbols': len(self.trading_pairs),
                'symbols_with_data': len(counts),
                'total_records': sum(counts.values()),
                'expected_total': len(self.trading_pairs) * expected_count,
                'health_score': health_score,
                'date_range': {
                    'start': date_range[0],
                    'end': date_range[1]
                },
                'status': 'healthy' if health_score >= 95 else 'needs_attention' if health_score >= 80 else 'unhealthy'
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.utcnow(),
                'status': 'error',
                'error': str(e)
            } 