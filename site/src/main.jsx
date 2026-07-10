import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// StrictMode intentionally omitted: Lenis + ScrollTrigger dislike the dev
// double-invoke, and this is a presentational marketing app.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
