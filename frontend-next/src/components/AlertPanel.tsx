'use client';
import React from 'react';
import styles from './AlertPanel.module.css';

interface Alert {
  id: number;
  title: string;
  location: string;
  source: string;
  timestamp: string;
  severity: 'High' | 'Medium' | 'Low' | 'Info';
}

const PLACEHOLDER_ALERTS: Alert[] = [
  {
    id: 1,
    title: 'Heavy Rainfall Warning',
    location: 'Maharashtra (Pune, Satara, Raigad)',
    source: 'IMD',
    timestamp: '10 Sep 2026, 12:30',
    severity: 'High',
  },
  {
    id: 2,
    title: 'Flash Flood Risk',
    location: 'Western Ghats (Maharashtra)',
    source: 'IMD',
    timestamp: '10 Sep 2026, 11:15',
    severity: 'Medium',
  },
  {
    id: 3,
    title: 'Thunderstorm Alert',
    location: 'Maharashtra (Pune, Nasik)',
    source: 'IMD',
    timestamp: '10 Sep 2026, 10:45',
    severity: 'Medium',
  },
  {
    id: 4,
    title: 'River Level Alert',
    location: 'Mula-Mutha (Pune)',
    source: 'CWC',
    timestamp: '10 Sep 2026, 09:20',
    severity: 'Low',
  },
];

function severityClass(severity: Alert['severity']): string {
  switch (severity) {
    case 'High':
      return styles.severityHigh;
    case 'Medium':
      return styles.severityMedium;
    case 'Low':
      return styles.severityLow;
    case 'Info':
      return styles.severityInfo;
  }
}

function severityIcon(severity: Alert['severity']): string {
  switch (severity) {
    case 'High':
      return '🔴';
    case 'Medium':
      return '🟠';
    case 'Low':
      return '🟡';
    case 'Info':
      return '🔵';
  }
}

export default function AlertPanel() {
  return (
    <div className={`panel ${styles.alertPanel}`}>
      <div className="panel-header">
        <span>Live Alert Intelligence</span>
        <a className={styles.viewAll} href="#">View All →</a>
      </div>

      <div className={styles.alertList}>
        {PLACEHOLDER_ALERTS.map((alert) => (
          <div key={alert.id} className={`${styles.alertCard} ${severityClass(alert.severity)}`}>
            <div className={styles.alertTop}>
              <span className={styles.alertIcon}>{severityIcon(alert.severity)}</span>
              <div className={styles.alertInfo}>
                <div className={styles.alertTitle}>{alert.title}</div>
                <div className={styles.alertLocation}>{alert.location}</div>
                <div className={styles.alertMeta}>
                  {alert.source} | {alert.timestamp}
                </div>
              </div>
              <span className={`${styles.severityBadge} ${severityClass(alert.severity)}`}>
                {alert.severity}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
