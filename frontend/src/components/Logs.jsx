import React, { useEffect, useState } from 'react';
import { getLogs } from '../lib/api';
import { FileText } from 'lucide-react';

export default function Logs() {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        getLogs().then(res => setLogs(res.data)).catch(console.error);
    }, []);

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <h2 className="text-2xl font-bold mb-6 text-slate-200 flex items-center gap-2">
                <FileText className="text-primary" /> Recent Conversations
            </h2>
            <div className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 shadow-lg">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-slate-400">
                        <thead className="bg-slate-900 text-slate-200 uppercase font-bold text-xs tracking-wider">
                            <tr>
                                <th className="p-4">Time</th>
                                <th className="p-4">Caller</th>
                                <th className="p-4 w-1/4">User Input</th>
                                <th className="p-4 w-1/4">Agent Response</th>
                                <th className="p-4">Emotion</th>
                                <th className="p-4">Latency</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                            {logs.map((log, i) => (
                                <tr key={i} className="hover:bg-slate-700/50 transition-colors group">
                                    <td className="p-4 font-mono text-xs text-slate-500 group-hover:text-slate-300">{log.timestamp}</td>
                                    <td className="p-4 font-mono text-xs">{log.phone_number || "Unknown"}</td>
                                    <td className="p-4 max-w-xs truncate text-white" title={log.user_input}>{log.user_input}</td>
                                    <td className="p-4 max-w-xs truncate text-primary font-medium" title={log.agent_response}>{log.agent_response}</td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${log.emotion === 'Anger' ? 'bg-red-900 text-red-200' : 'bg-slate-700 text-slate-300'}`}>
                                            {log.emotion || "Neutral"}
                                        </span>
                                    </td>
                                    <td className="p-4 font-mono text-xs">{log.latency_ms}ms</td>
                                </tr>
                            ))}
                            {logs.length === 0 && (
                                <tr>
                                    <td colSpan="6" className="p-10 text-center text-slate-500">No logs found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
