import React, { useState, useEffect } from 'react';
import { getConfig, updateConfig } from '../lib/api';
import { Key, Shield, Save, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react';

export default function ApiSettings() {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showKeys, setShowKeys] = useState({});
    const [message, setMessage] = useState(null);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        try {
            const res = await getConfig();
            setConfig(res.data);
        } catch (err) {
            console.error("Failed to load config", err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage(null);
        try {
            await updateConfig(config);
            setMessage({ type: 'success', text: 'API Settings updated successfully!' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            setMessage({ type: 'error', text: 'Failed to update settings: ' + err.message });
        } finally {
            setSaving(false);
        }
    };

    const toggleKeyVisibility = (key) => {
        setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const updateApiField = (field, value) => {
        setConfig({
            ...config,
            api: { ...config.api, [field]: value }
        });
    };

    if (loading || !config) return <div className="p-8 text-slate-400">Loading vault...</div>;

    return (
        <div className="p-6 max-w-5xl mx-auto text-slate-200">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h2 className="text-2xl font-bold flex items-center gap-2">
                        <Shield className="text-primary" /> API Settings & Security
                    </h2>
                    <p className="text-slate-400 text-sm mt-1">Manage service credentials and safety protocols.</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-primary hover:bg-orange-600 px-6 py-2 rounded-lg font-bold flex items-center gap-2 disabled:opacity-50 transition-all shadow-lg shadow-orange-900/20"
                >
                    <Save size={18} /> {saving ? "Saving..." : "Save Changes"}
                </button>
            </div>

            {message && (
                <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-2 ${message.type === 'success' ? 'bg-green-900/20 border border-green-500/50 text-green-400' : 'bg-red-900/20 border border-red-500/50 text-red-400'
                    }`}>
                    {message.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                    {message.text}
                </div>
            )}

            <div className="grid grid-cols-1 gap-8">
                {/* API Credentials */}
                <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-sm">
                    <div className="p-4 bg-slate-700/30 border-b border-slate-700 flex items-center gap-2 text-primary font-semibold">
                        <Key size={18} /> Service API Keys
                    </div>
                    <div className="p-6 space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <KeyInput
                                label="Groq API Key"
                                value={config.api.groq_api_key}
                                show={showKeys.groq}
                                onToggle={() => toggleKeyVisibility('groq')}
                                onChange={(e) => updateApiField('groq_api_key', e.target.value)}
                                placeholder="gsk_..."
                            />
                            <KeyInput
                                label="Deepgram API Key"
                                value={config.api.deepgram_api_key}
                                show={showKeys.dg}
                                onToggle={() => toggleKeyVisibility('dg')}
                                onChange={(e) => updateApiField('deepgram_api_key', e.target.value)}
                                placeholder="cacf..."
                            />
                            <KeyInput
                                label="ElevenLabs API Key"
                                value={config.api.elevenlabs_api_key}
                                show={showKeys.eleven}
                                onToggle={() => toggleKeyVisibility('eleven')}
                                onChange={(e) => updateApiField('elevenlabs_api_key', e.target.value)}
                                placeholder="c018..."
                            />
                            <KeyInput
                                label="Tunnel URL (Webhook Base)"
                                value={config.api.tunnel_url}
                                show={true}
                                onChange={(e) => updateApiField('tunnel_url', e.target.value)}
                                placeholder="https://..."
                                isPublic={true}
                            />
                        </div>

                        <div className="pt-4 border-t border-slate-700/50">
                            <h4 className="text-xs uppercase font-bold text-slate-500 mb-4 tracking-wider">Telephony (Twilio)</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <KeyInput
                                    label="Account SID"
                                    value={config.api.twilio_account_sid}
                                    show={showKeys.twilio_sid}
                                    onToggle={() => toggleKeyVisibility('twilio_sid')}
                                    onChange={(e) => updateApiField('twilio_account_sid', e.target.value)}
                                    placeholder="AC..."
                                />
                                <KeyInput
                                    label="Auth Token"
                                    value={config.api.twilio_auth_token}
                                    show={showKeys.twilio_token}
                                    onToggle={() => toggleKeyVisibility('twilio_token')}
                                    onChange={(e) => updateApiField('twilio_auth_token', e.target.value)}
                                    placeholder="..."
                                />
                                <KeyInput
                                    label="Twilio Phone Number"
                                    value={config.api.twilio_phone_number}
                                    show={true}
                                    onChange={(e) => updateApiField('twilio_phone_number', e.target.value)}
                                    placeholder="+1..."
                                    isPublic={true}
                                />
                            </div>
                        </div>

                        <div className="pt-4 border-t border-slate-700/50">
                            <h4 className="text-xs uppercase font-bold text-slate-500 mb-4 tracking-wider">Database (Supabase)</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <KeyInput
                                    label="Supabase URL"
                                    value={config.api.supabase_url}
                                    show={true}
                                    onChange={(e) => updateApiField('supabase_url', e.target.value)}
                                    placeholder="https://..."
                                    isPublic={true}
                                />
                                <KeyInput
                                    label="Service Key"
                                    value={config.api.supabase_service_key}
                                    show={showKeys.supabase}
                                    onToggle={() => toggleKeyVisibility('supabase')}
                                    onChange={(e) => updateApiField('supabase_service_key', e.target.value)}
                                    placeholder="..."
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Security Section Placeholder */}
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm opacity-60">
                    <div className="flex items-center gap-2 font-semibold text-slate-400 mb-2">
                        <Shield size={18} /> Advanced Security (Pro)
                    </div>
                    <p className="text-sm">Vulnerability scanning and PII redaction are coming in a future update.</p>
                </div>
            </div>
        </div>
    );
}

function KeyInput({ label, value, show, onToggle, onChange, placeholder, isPublic = false }) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400 ml-1">{label}</label>
            <div className="relative group">
                <input
                    type={isPublic || show ? "text" : "password"}
                    value={value}
                    onChange={onChange}
                    placeholder={placeholder}
                    className="w-full bg-slate-900 border border-slate-700/50 rounded-lg py-2 px-3 text-sm font-mono text-primary placeholder:text-slate-700 focus:outline-none focus:border-primary transition-all pr-10"
                />
                {!isPublic && (
                    <button
                        type="button"
                        onClick={onToggle}
                        className="absolute right-2 top-1.5 p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors"
                    >
                        {show ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                )}
            </div>
        </div>
    );
}
