'use client';
import React from 'react';
import styles from './IndiaMap.module.css';

export default function IndiaMap() {
  return (
    <div className={`panel ${styles.mapPanel}`}>
      {/* Location + Layer Selectors */}
      <div className={styles.selectors}>
        <select className={styles.dropdown}>
          <option>📍 Pune, Maharashtra</option>
          <option>Delhi</option>
          <option>Mumbai, Maharashtra</option>
          <option>Chennai, Tamil Nadu</option>
          <option>Kolkata, West Bengal</option>
          <option>Bengaluru, Karnataka</option>
        </select>
        <select className={styles.dropdown}>
          <option>Weather Layers</option>
          <option>Rainfall</option>
          <option>Temperature</option>
          <option>Wind</option>
          <option>Satellite</option>
        </select>
      </div>

      {/* Map Title + Legend Keys */}
      <div className={styles.mapHeader}>
        <span className={styles.mapTitle}>India Weather & Hazard Map</span>
        <div className={styles.legendKeys}>
          <span className={styles.lk}><span className={`${styles.dot} ${styles.dotBlue}`}></span> Rainfall</span>
          <span className={styles.lk}><span className={`${styles.dot} ${styles.dotRed}`}></span> Heat</span>
          <span className={styles.lk}><span className={`${styles.dot} ${styles.dotGreen}`}></span> Wind</span>
          <span className={styles.lk}><span className={`${styles.dot} ${styles.dotPurple}`}></span> Cyclone</span>
          <span className={styles.lk}><span className={`${styles.dot} ${styles.dotOrange}`}></span> Alert</span>
        </div>
      </div>

      {/* Map Area */}
      <div className={styles.mapContainer}>
        {/* SVG India map — Y-axis inverted (SVG Y increases downward) */}
        <svg viewBox="68 6 30 32" className={styles.mapSvg} xmlns="http://www.w3.org/2000/svg">
          {/* Simplified India outline - corrected orientation */}
          <path
            d="M76.8,7.5 L78,7.2 L79.5,7.5 L80.5,7 L82,7.8 L83.5,7.5 L85,8 L87,8.5
               L88.5,9.5 L90,10 L91.5,11 L93,12 L94,13.5 L95,15 L96,17
               L96.5,19 L96,21 L95,22.5 L93.5,24 L92,25 L90.5,26
               L89,27 L87.5,28 L86,29 L85,30 L83.5,31 L82,32
               L81,33 L80,34 L79.5,35 L79,36 L79.5,37
               L79,36.5 L78,35.5 L77,34 L76,32.5 L75,31 L74,29
               L73,27 L72,25 L71.5,23 L71,21 L70.5,19 L70,17
               L70,15 L70.5,13 L71.5,11.5 L73,10 L74.5,9 L76,8 Z"
            fill="#e8f4f8"
            stroke="#94a3b8"
            strokeWidth="0.2"
          />

          {/* Major cities — positioned correctly on India geography */}
          {[
            { x: 77.1, y: 11.5, name: 'Delhi', alert: false },
            { x: 72.8, y: 22.0, name: 'Mumbai', alert: true },
            { x: 73.9, y: 21.5, name: 'Pune', alert: true },
            { x: 88.4, y: 16.5, name: 'Kolkata', alert: false },
            { x: 80.3, y: 28.5, name: 'Chennai', alert: false },
            { x: 77.6, y: 27.0, name: 'Bengaluru', alert: false },
            { x: 72.6, y: 17.0, name: 'Ahmedabad', alert: false },
          ].map((city) => (
            <g key={city.name}>
              <circle
                cx={city.x}
                cy={city.y}
                r={city.alert ? 0.45 : 0.3}
                fill={city.alert ? '#ef4444' : '#3b82f6'}
                opacity={0.9}
              />
              {city.alert && (
                <circle
                  cx={city.x}
                  cy={city.y}
                  r={0.7}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth={0.1}
                  opacity={0.5}
                  className={styles.pulse}
                />
              )}
              <text
                x={city.x + 0.6}
                y={city.y + 0.2}
                fontSize="0.7"
                fill="#334155"
                fontFamily="Inter, sans-serif"
              >
                {city.name}
              </text>
            </g>
          ))}

          {/* Water bodies labels */}
          <text x="69" y="20" fontSize="0.55" fill="#93c5fd" fontStyle="italic" fontFamily="Inter">Arabian</text>
          <text x="69" y="20.7" fontSize="0.55" fill="#93c5fd" fontStyle="italic" fontFamily="Inter">Sea</text>
          <text x="85" y="30" fontSize="0.55" fill="#93c5fd" fontStyle="italic" fontFamily="Inter">Bay of</text>
          <text x="85" y="30.7" fontSize="0.55" fill="#93c5fd" fontStyle="italic" fontFamily="Inter">Bengal</text>
          <text x="76" y="38" fontSize="0.55" fill="#93c5fd" fontStyle="italic" fontFamily="Inter">Indian Ocean</text>
        </svg>

        {/* Map Controls */}
        <div className={styles.mapControls}>
          <button className={styles.zoomBtn}>+</button>
          <button className={styles.zoomBtn}>−</button>
        </div>

        {/* Satellite toggle */}
        <div className={styles.satToggle}>
          <button className={styles.satBtn}>Satellite</button>
        </div>
      </div>

      {/* Bottom Legend */}
      <div className={styles.legend}>
        <div className={styles.legendSection}>
          <div className={styles.legendTitle}>Rainfall Intensity (mm/hr)</div>
          <div className={styles.gradientBar}></div>
          <div className={styles.gradientLabels}>
            <span>0</span><span>5</span><span>10</span><span>20</span><span>50</span><span>100+</span>
          </div>
        </div>
        <div className={styles.legendSection}>
          <div className={styles.legendTitle}>Active Hazards</div>
          <div className={styles.hazardList}>
            <div className={styles.hazardItem}><span className={`${styles.dot} ${styles.dotBlue}`}></span> Heavy Rain (4)</div>
            <div className={styles.hazardItem}><span className={`${styles.dot} ${styles.dotYellow}`}></span> Thunderstorm (1)</div>
            <div className={styles.hazardItem}><span className={`${styles.dot} ${styles.dotPurple}`}></span> Cyclone (0)</div>
            <div className={styles.hazardItem}><span className={`${styles.dot} ${styles.dotOrange}`}></span> Heat Wave (0)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
