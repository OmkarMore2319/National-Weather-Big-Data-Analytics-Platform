import React from 'react';
import { CloudLightning, ShieldCheck, MapPin, Radio, Activity, RefreshCw } from 'lucide-react';

export function Navbar({ activeTab, setActiveTab, connectionStatus, totalEventsCount, onRefresh }) {
  return (
    <header className="bg-[#1F5B8C] text-white shadow-elevated sticky top-0 z-30 border-b border-[#184870]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Name */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center border border-white/20 backdrop-blur-sm shadow-inner">
              <CloudLightning className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                  National Weather Analytics Platform
                </h1>
                <span className="text-[10px] font-semibold tracking-wider bg-white/20 text-white px-2 py-0.5 rounded uppercase">
                  PS 26069
                </span>
              </div>
              <p className="text-xs text-blue-100 hidden sm:block">
                Multi-Source Verification & Geospatial Weather Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center space-x-4">
            {/* View Switcher */}
            <nav className="flex space-x-1 bg-black/20 p-1 rounded-lg border border-white/10">
              <button
                onClick={() => setActiveTab('public')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === 'public'
                    ? 'bg-white text-[#1F5B8C] shadow-sm font-semibold'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <MapPin className="w-3.5 h-3.5" />
                <span>Public Dashboard</span>
              </button>

              <button
                onClick={() => setActiveTab('admin')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === 'admin'
                    ? 'bg-white text-[#1F5B8C] shadow-sm font-semibold'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Admin Console</span>
              </button>
            </nav>

            {/* Connection Status Indicator */}
            <div className="hidden md:flex items-center space-x-2 bg-white/10 px-2.5 py-1.2 rounded-full border border-white/15 text-xs">
              {connectionStatus === 'connected' ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-[11px] font-medium text-emerald-200">Live WS</span>
                </>
              ) : connectionStatus === 'fallback-polling' ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-amber-400"></span>
                  <span className="text-[11px] font-medium text-amber-200">10s Polling</span>
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-slate-400 animate-pulse"></span>
                  <span className="text-[11px] font-medium text-slate-300">Connecting...</span>
                </>
              )}
            </div>

            {/* Manual Refresh */}
            <button
              onClick={onRefresh}
              title="Refresh Data"
              className="p-1.5 rounded-md bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
