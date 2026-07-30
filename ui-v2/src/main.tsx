import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ModeProvider } from './theme'
import './index.css'

// ModeProvider wraps App rather than living inside it: the light/dark value has
// to be readable by the shell and by the chart from the same single source, and
// it sets <html data-mode> before the first paint so index.css agrees with the
// inline styles from frame one.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ModeProvider>
      <App />
    </ModeProvider>
  </React.StrictMode>,
)
