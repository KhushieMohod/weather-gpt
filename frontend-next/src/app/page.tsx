import React from 'react';
import IndiaMap from '@/components/IndiaMap';
import WeatherIntelligence from '@/components/WeatherIntelligence';
import AlertPanel from '@/components/AlertPanel';
import Chatbot from '@/components/Chatbot';

export default function Home() {
  return (
    <main className="main-content">
      <div className="column left-column">
        <IndiaMap />
      </div>
      
      <div className="column center-column">
        <WeatherIntelligence />
      </div>
      
      <div className="column right-column">
        <AlertPanel />
        <Chatbot />
      </div>
    </main>
  );
}
