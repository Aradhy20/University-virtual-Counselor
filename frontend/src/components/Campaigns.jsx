import React, { useState } from 'react';
import { uploadCampaign, startCampaign } from '../lib/api';
import { Upload, Play, PhoneCall, CheckCircle, AlertCircle } from 'lucide-react';

export default function Campaigns() {
    const [file, setFile] = useState(null);
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
        setResult(null);
        setContacts([]);
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await uploadCampaign(formData);
            setContacts(res.data.contacts);
        } catch (err) {
            alert("Error uploading CSV: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStart = async () => {
        if (contacts.length === 0) return;
        if (!confirm(`Start calling ${contacts.length} numbers?`)) return;

        setLoading(true);
        try {
            const res = await startCampaign(contacts);
            setResult(res.data);
        } catch (err) {
            alert("Error starting campaign: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto text-slate-200">
            <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                    <PhoneCall className="text-primary" /> Campaign Manager (Bulk Dialer)
                </h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Upload Section */}
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Upload size={20} className="text-primary" /> Upload Contact List
                    </h3>
                    <div className="space-y-4">
                        <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50 text-xs text-slate-400">
                            <p className="font-semibold mb-1">CSV Format Required</p>
                            <code className="text-green-400">Name, Phone</code>
                            <p className="mt-1">Allows bulk calling. Numbers must be in E.164 format (e.g., +919876543210).</p>
                        </div>

                        <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileChange}
                            className="block w-full text-sm text-slate-300 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-orange-600 cursor-pointer bg-slate-900 rounded-lg border border-slate-700"
                        />

                        <button
                            onClick={handleUpload}
                            disabled={!file || loading}
                            className="w-full bg-slate-700 hover:bg-slate-600 py-2.5 rounded-lg font-medium disabled:opacity-50 transition-colors text-sm"
                        >
                            {loading ? "Processing..." : "Parse CSV File"}
                        </button>
                    </div>
                </div>

                {/* Results Section */}
                {result && (
                    <div className={`p-6 rounded-xl border shadow-lg ${result.failed > 0 ? 'bg-orange-900/10 border-orange-500/30' : 'bg-green-900/10 border-green-500/30'}`}>
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            {result.failed > 0 ? <AlertCircle className="text-orange-500" /> : <CheckCircle className="text-green-500" />}
                            Execution Summary
                        </h3>
                        <div className="grid grid-cols-3 gap-4 text-center">
                            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                                <div className="text-3xl font-bold">{result.total}</div>
                                <div className="text-xs text-slate-400 uppercase tracking-wider mt-1">Total</div>
                            </div>
                            <div className="bg-green-900/20 p-4 rounded-lg border border-green-500/20">
                                <div className="text-3xl font-bold text-green-400">{result.queued}</div>
                                <div className="text-xs text-green-300/70 uppercase tracking-wider mt-1">Queued</div>
                            </div>
                            <div className="bg-red-900/20 p-4 rounded-lg border border-red-500/20">
                                <div className="text-3xl font-bold text-red-400">{result.failed}</div>
                                <div className="text-xs text-red-300/70 uppercase tracking-wider mt-1">Failed</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Preview Table */}
            {contacts.length > 0 && (
                <div className="mt-8 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="p-4 bg-slate-800 flex justify-between items-center border-b border-slate-700">
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-white">Campaign Preview</h3>
                            <span className="bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full text-xs font-bold">{contacts.length} Records</span>
                        </div>
                        <button
                            onClick={handleStart}
                            disabled={loading}
                            className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 disabled:opacity-50 transition-colors shadow-lg shadow-green-900/20"
                        >
                            <Play size={18} fill="currentColor" /> {loading ? "Initiating..." : "Launch Campaign"}
                        </button>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                        <table className="w-full text-left text-sm text-slate-300">
                            <thead className="bg-slate-900 sticky top-0 text-slate-400 uppercase text-xs font-bold tracking-wider shadow-sm">
                                <tr>
                                    <th className="p-4">#</th>
                                    <th className="p-4">Name</th>
                                    <th className="p-4">Phone Number</th>
                                    <th className="p-4 text-center">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700/50">
                                {contacts.map((c, i) => (
                                    <tr key={i} className="hover:bg-slate-700/30 transition-colors">
                                        <td className="p-4 text-slate-500 w-16 font-mono text-xs">{i + 1}</td>
                                        <td className="p-4 font-medium text-white">{c.name}</td>
                                        <td className="p-4 font-mono text-primary">{c.phone}</td>
                                        <td className="p-4 text-center">
                                            <span className="bg-slate-700/50 px-3 py-1 rounded-full text-xs text-slate-300 border border-slate-600">Queued</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
