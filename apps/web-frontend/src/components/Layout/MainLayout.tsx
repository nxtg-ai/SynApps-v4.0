/**
 * MainLayout component
 * Provides consistent layout with sidebar navigation and header
 */
import React, { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import NotificationCenter from '../Notifications/NotificationCenter';
import './MainLayout.css';

interface MainLayoutProps {
  children: ReactNode;
  title: string;
  actions?: ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children, title, actions }) => {
  const location = useLocation();
  
  // Navigation items
  const navItems = [
    { path: '/dashboard', icon: '🏠', label: 'Dashboard' },
    { path: '/editor', icon: '🔄', label: 'Workflow Editor' },
    { path: '/history', icon: '📋', label: 'Run History' },
    { path: '/applets', icon: '🧩', label: 'Applet Library' },
    { path: '/settings', icon: '⚙️', label: 'Settings' }
  ];
  
  return (
    <div className="main-layout">
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🧠</span>
          <span className="logo-text">SynApps</span>
        </div>
        
        <nav className="nav-menu">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname.startsWith(item.path) ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </nav>
        
        <div className="version-info">
          <span>SynApps MVP v0.1.0</span>
        </div>
      </aside>
      
      <main className="main-content">
        <header className="header">
          <h1 className="page-title">{title}</h1>
          
          <div className="header-actions">
            {actions}
            <NotificationCenter />
          </div>
        </header>
        
        <div className="content">
          {children}
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
