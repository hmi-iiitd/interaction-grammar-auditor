import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dataset from './pages/Dataset';
import Overview from './pages/Overview';
import Timeline from './pages/Timeline';
import ContractQA from './pages/ContractQA';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Upload from './pages/Upload';
import AuthorScenario from './pages/AuthorScenario';
import ScenarioUnderstanding from './pages/ScenarioUnderstanding';
import ClarificationWizard from './pages/ClarificationWizard';
import ContractPreview from './pages/ContractPreview';
import ValidateAndMap from './pages/ValidateAndMap';
import LockContract from './pages/LockContract';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dataset />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/scenario/:id" element={<Overview />} />
            <Route path="/timeline/:id" element={<Timeline />} />
            <Route path="/qa/:id" element={<ContractQA />} />
            <Route path="/report/:id" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            {/* Phase 6: Authoring flow */}
            <Route path="/author" element={<AuthorScenario />} />
            <Route path="/author/understand/:id" element={<ScenarioUnderstanding />} />
            <Route path="/author/clarify/:id" element={<ClarificationWizard />} />
            <Route path="/author/preview/:id" element={<ContractPreview />} />
            <Route path="/author/validate/:id" element={<ValidateAndMap />} />
            <Route path="/author/lock/:id" element={<LockContract />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
