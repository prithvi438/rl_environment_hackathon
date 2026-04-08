import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', background: '#450a0a', color: '#fecaca', height: '100vh', width: '100vw', fontFamily: 'monospace' }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>⚠️ Dashboard Crash Detected</h2>
          <pre style={{ background: '#000', padding: '1rem', borderRadius: '0.5rem', overflow: 'auto' }}>
            {this.state.error && this.state.error.toString()}
          </pre>
          <p style={{ marginTop: '1rem' }}>Please report this error message to the developer.</p>
          <button 
            onClick={() => window.location.reload()}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#ef4444', color: 'white', border: 'none', borderRadius: '0.25rem', cursor: 'pointer' }}
          >
            Retry Launch
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
