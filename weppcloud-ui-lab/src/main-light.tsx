import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index-light.css'
import AppLight from './AppLight.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppLight />
  </StrictMode>,
)
