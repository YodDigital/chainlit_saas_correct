import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App'; // Your main App component
import './index.css'; // Global styles (optional)

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

