import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import Config from './components/Config';
import Logs from './components/Logs';
import Playground from './components/Playground';
import Campaigns from './components/Campaigns';
import ApiSettings from './components/ApiSettings';
import { Activity, Settings, FileText, MessageSquare, Database, PhoneCall, ShieldCheck } from 'lucide-react';

function App() {
    const [activeTab, setActiveTab] = useState('dashboard');

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard': return <Dashboard />;
            case 'config': return <Config />;
            case 'logs': return <Logs />;
            case 'campaigns': return <Campaigns />;
            case 'api': return <ApiSettings />;
            case 'playground': return <Playground />;
            default: return <Dashboard />;
        }
    };

    return (
        <div className="flex h-screen bg-slate-900 text-slate-100 font-sans selection:bg-primary/30">
            {/* Sidebar */}
            <aside className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col shadow-xl z-10">
                <div className="p-8 border-b border-slate-700/50">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3 tracking-tight">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white">
                            <Activity size={20} />
                        </div>
                        Aditi Admin
                    </h1>
                    <p className="text-xs text-slate-400 mt-2 font-medium tracking-wide uppercase px-1">Enterprise Control Center</p>
                </div>

                <nav className="flex-1 p-6 space-y-3">
                    <NavItem icon={<Activity size={20} />} label="System Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
                    <NavItem icon={<Settings size={20} />} label="Configuration Studio" active={activeTab === 'config'} onClick={() => setActiveTab('config')} />
                    <NavItem icon={<PhoneCall size={20} />} label="Campaign Manager" active={activeTab === 'campaigns'} onClick={() => setActiveTab('campaigns')} />
                    <NavItem icon={<ShieldCheck size={20} />} label="API & Security Vault" active={activeTab === 'api'} onClick={() => setActiveTab('api')} />
                    <NavItem icon={<FileText size={20} />} label="Conversation Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
                    <div className="pt-4 pb-2">
                        <div className="h-px bg-slate-700/50 w-full"></div>
                    </div>
                    <NavItem icon={<MessageSquare size={20} />} label="Test Playground" active={activeTab === 'playground'} onClick={() => setActiveTab('playground')} />
                    <NavItem icon={<Database size={20} />} label="Knowledge Base" active={activeTab === 'kb'} onClick={() => alert("KB Manager Coming Soon via Admin API")} />
                </nav>

                <div className="p-6 border-t border-slate-700/50">
                    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                            <span className="text-xs font-semibold text-slate-300">System Online</span>
                        </div>
                        <p className="text-[10px] text-slate-500">v3.1.0 Enterprise</p>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto bg-slate-950/50 relative">
                <div className="absolute inset-0 bg-grid-slate-900/[0.04] bg-[bottom_1px_center] mask-image-linear-gradient(to_bottom,transparent,black)]"></div>
                <div className="relative z-10">
                    {renderContent()}
                </div>
            </main>
        </div>
    );
}

const NavItem = ({ icon, label, active, onClick }) => (
    <button
        onClick={onClick}
        className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-200 group ${active
            ? 'bg-primary text-white shadow-lg shadow-primary/20 translate-x-1'
            : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-100 hover:translate-x-1'
            }`}
    >
        {icon}
        <span className="font-medium text-sm tracking-wide">{label}</span>
    </button>
);

export default App;
