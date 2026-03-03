import React, { useEffect, useState } from 'react';
import { getStats } from '../lib/api';
import { BarChart, Activity, PhoneCall } from 'lucide-react';

export default function Dashboard() {
    const [stats, setStats] = useState(null);

    useEffect(() => {
        getStats().then(res => setStats(res.data)).catch(console.error);
    }, []);

    if (!stats) return <div className="p-10 text-slate-400 animate-pulse">Loading core metrics...</div>;

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2 text-white">
                <Activity className="text-primary" /> System Overview
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard
                    icon={<PhoneCall className="w-6 h-6" />}
                    label="Total Simulated Calls"
                    value={stats.total_calls}
                />
                <StatCard
                    icon={<Activity className="w-6 h-6" />}
                    label="Avg Call Duration"
                    value={stats.avg_duration}
                />
                <StatCard
                    icon={<BarChart className="w-6 h-6" />}
                    label="Sentiment Index"
                    value={stats.sentiment_score}
                />
            </div>

            <div className="mt-8 bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 className="text-lg font-semibold mb-4 text-slate-200">Recent Activity</h3>
                <p className="text-slate-400">System is running normally. No critical alerts.</p>
            </div>
        </div>
    );
}

const StatCard = ({ icon, label, value }) => (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg hover:border-primary transition-colors">
        <div className="flex items-center gap-4 mb-2">
            <div className="text-primary p-2 bg-slate-900 rounded-lg">{icon}</div>
            <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">{label}</h3>
        </div>
        <div className="text-3xl font-bold text-white mt-1">{value}</div>
    </div>
);
