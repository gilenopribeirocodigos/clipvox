import { useState } from 'react'
import Landing from './pages/Landing.jsx'
import Dashboard from './pages/Dashboard.jsx'

export default function App() {
  // Roteamento simples sem library externa para MVP
  const [page, setPage] = useState('landing')

  // Expor função de navegação globalmente para uso nos componentes
  window.navigateTo = setPage

  switch (page) {
    case 'dashboard':
      return <Dashboard onBack={() => setPage('landing')} />
    case 'landing':
    default:
      return <Landing onGetStarted={() => setPage('dashboard')} />
  }
}
