'use client';
import React, { useState } from 'react';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const [activeItem, setActiveItem] = useState('Home');

  const navItems = [
    { name: 'Home', icon: '🏠' },
    { name: 'Map & Layers', icon: '🗺️' },
    { name: 'Weather Intelligence', icon: '📊' },
    { name: 'Alerts & Warnings', icon: '⚠️' },
    { name: 'Chat with WeatherGPT', icon: '💬' },
    { name: 'Reports', icon: '📄' },
    { name: 'Settings', icon: '⚙️' },
  ];

  return (
    <nav className={styles.sidebar}>
      <ul className={styles.navList}>
        {navItems.map((item) => (
          <li
            key={item.name}
            className={`${styles.navItem} ${
              activeItem === item.name ? styles.active : ''
            }`}
            onClick={() => setActiveItem(item.name)}
          >
            <span className={styles.icon}>{item.icon}</span>
            <span className={styles.label}>{item.name}</span>
          </li>
        ))}
      </ul>
      
      <div className={styles.footer}>
        <div className={styles.footerText}>WeatherGPT</div>
        <div className={styles.footerSub}>SIH 2026 | #26068</div>
      </div>
    </nav>
  );
}
