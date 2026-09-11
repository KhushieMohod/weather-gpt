'use client';
import React, { useState, useEffect } from 'react';
import styles from './Header.module.css';

export default function Header() {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleString('en-IN', {
          weekday: 'short',
          day: '2-digit',
          month: 'short',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
          timeZoneName: 'short',
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 10000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <div className={styles.emblem}>
          {/* Placeholder for State Emblem of India */}
          <span className={styles.emblemText}>GOI</span>
        </div>
        <div className={styles.titleGroup}>
          <div className={styles.ministry}>Ministry of Earth Sciences</div>
          <div className={styles.title}>
            <span className={styles.logoIcon}>☁️</span> WeatherGPT
          </div>
          <div className={styles.subtitle}>Multi-Source Disaster Weather Intelligence</div>
        </div>
      </div>
      
      <div className={styles.center}>
        <span className={styles.tagline}>Integrated | Verified | Evidence-based</span>
      </div>
      
      <div className={styles.right}>
        <div className={styles.agencies}>
          <div className={styles.agency}>IMD</div>
          <div className={styles.agency}>MOSDAC</div>
          <div className={styles.agency}>NDMA</div>
          <div className={styles.agency}>CWC</div>
        </div>
        
        <div className={styles.timeStatus}>
          <div className={styles.time}>{time || 'Loading...'}</div>
          <div className={styles.status}>
            <span className={styles.statusDot}></span> System Online
          </div>
        </div>
      </div>
    </header>
  );
}
