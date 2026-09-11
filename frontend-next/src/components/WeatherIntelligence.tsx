'use client';
import React from 'react';
import styles from './WeatherIntelligence.module.css';

export default function WeatherIntelligence() {
  return (
    <div className={styles.container}>
      {/* Weather Metrics */}
      <div className={`panel ${styles.metricsPanel}`}>
        <div className="panel-header">
          <span>Weather Intelligence - Pune, Maharashtra</span>
          <span className={styles.lastUpdated}>Last Updated: 15:38 IST ↻</span>
        </div>
        
        <div className={styles.metricsGrid}>
          <div className={styles.mainTemp}>
            <div className={styles.tempValue}>27.3°C</div>
            <div className={styles.tempSub}>Feels like 29.1°C</div>
            <div className={styles.tempDesc}>Light Rain</div>
          </div>
          
          <div className={styles.metricItem}>
            <div className={styles.metricIcon}>💧</div>
            <div className={styles.metricValue}>12.4 mm</div>
            <div className={styles.metricLabel}>Rainfall (24h)</div>
            <div className={styles.metricDesc}>Moderate</div>
          </div>
          
          <div className={styles.metricItem}>
            <div className={styles.metricIcon}>💦</div>
            <div className={styles.metricValue}>88%</div>
            <div className={styles.metricLabel}>Humidity</div>
            <div className={styles.metricDesc}>High</div>
          </div>
          
          <div className={styles.metricItem}>
            <div className={styles.metricIcon}>💨</div>
            <div className={styles.metricValue}>6.2 km/h</div>
            <div className={styles.metricLabel}>Wind (NW)</div>
            <div className={styles.metricDesc}>Light</div>
          </div>
          
          <div className={styles.metricItem}>
            <div className={styles.metricIcon}>⏱️</div>
            <div className={styles.metricValue}>1002 hPa</div>
            <div className={styles.metricLabel}>Pressure</div>
            <div className={styles.metricDesc}>Normal</div>
          </div>
        </div>
      </div>

      {/* 24-Hour Trend */}
      <div className={`panel ${styles.trendPanel}`}>
        <div className="panel-header">24-Hour Trend</div>
        <div className={styles.chartPlaceholder}>
          <div className={styles.chartText}>Trend Chart Placeholder</div>
        </div>
      </div>

      {/* Forecast */}
      <div className={`panel ${styles.forecastPanel}`}>
        <div className="panel-header">Forecast (Next 5 Days)</div>
        <div className={styles.forecastGrid}>
          {[
            { day: 'Tue', date: '10 Sep', icon: '🌧️', temp: '28° / 22°', desc: 'Light Rain', rain: '12 mm' },
            { day: 'Wed', date: '11 Sep', icon: '☁️', temp: '30° / 23°', desc: 'Cloudy', rain: '2 mm' },
            { day: 'Thu', date: '12 Sep', icon: '⛅', temp: '31° / 23°', desc: 'Partly Cloudy', rain: '0 mm' },
            { day: 'Fri', date: '13 Sep', icon: '☀️', temp: '32° / 24°', desc: 'Mostly Clear', rain: '0 mm' },
            { day: 'Sat', date: '14 Sep', icon: '☀️', temp: '33° / 24°', desc: 'Clear', rain: '0 mm' },
          ].map((item, idx) => (
            <div key={idx} className={styles.forecastItem}>
              <div className={styles.fcDay}>{item.day}</div>
              <div className={styles.fcDate}>{item.date}</div>
              <div className={styles.fcIcon}>{item.icon}</div>
              <div className={styles.fcTemp}>{item.temp}</div>
              <div className={styles.fcDesc}>{item.desc}</div>
              <div className={styles.fcRain}>{item.rain}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Source Fusion */}
      <div className={`panel ${styles.fusionPanel}`}>
        <div className="panel-header">Source Fusion & Credibility</div>
        <div className={styles.fusionGrid}>
          <div className={styles.sourceList}>
            {[
              { name: 'IMD', status: 'LIVE', score: '0.82', color: 'var(--status-live)' },
              { name: 'MOSDAC', status: 'FALLBACK', score: '0.64', color: 'var(--status-fallback)' },
              { name: 'GFS', status: 'LIVE', score: '0.76', color: 'var(--status-live)' },
              { name: 'ERA5', status: 'LIVE', score: '0.73', color: 'var(--status-live)' },
              { name: 'CWC', status: 'NO DATA', score: '-', color: 'var(--status-nodata)' },
            ].map((src, idx) => (
              <div key={idx} className={styles.sourceItem}>
                <div className={styles.srcName}>{src.name}</div>
                <div className={styles.srcStatus} style={{ color: src.color }}>
                  <span className={styles.statusDot} style={{ backgroundColor: src.color }}></span>
                  {src.status}
                </div>
                <div className={styles.srcScore}>{src.score}</div>
              </div>
            ))}
          </div>
          <div className={styles.avgCredibility}>
            <div className={styles.avgCircle}>
              <span className={styles.avgLabel}>Avg. Credibility</span>
              <span className={styles.avgValue}>0.74</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
