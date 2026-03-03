import React, { useEffect, useState } from 'react';
import { getConfig, updateConfig } from '../lib/api';
import { Save, Settings, Mic, Brain, Shield } from 'lucide-react';

export default function Config() {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        getConfig().then(res => setConfig(res.data)).catch(console.error);
    }, []);

    const handleSave = async () => {
        setLoading(true);
        try {
            await updateConfig(config);
            alert("Configuration Saved Successfully!");
        } catch (e) {
            alert("Failed to save: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (section, field, value) => {
        setConfig(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                [field]: value
            }
        }));
    };

    if (!config) return <div className="p-10 text-slate-400 animate-pulse">Loading settings...</div>;

    return (
        <div className="p-6 max-w-7xl mx-auto text-slate-200">
            <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-bold flex items-center gap-2"><Settings className="text-primary" /> Agent Configuration</h2>
                <button
                    onClick={handleSave}
                    disabled={loading}
                    className="bg-primary hover:bg-orange-600 px-6 py-2 rounded-lg font-medium flex gap-2 items-center disabled:opacity-50 transition-colors"
                >
                    <Save size={18} /> {loading ? "Saving..." : "Save Changes"}
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* LLM Section */}
                <Section title="Cognitive Engine (LLM)" icon={<Brain size={20} />}>
                    <Field label="Model Identifier" value={config.llm.model_name} onChange={(v) => handleChange('llm', 'model_name', v)} />
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Temperature (Creativity)" type="number" step="0.1" min="0" max="2" value={config.llm.temperature} onChange={(v) => handleChange('llm', 'temperature', parseFloat(v))} />
                        <Field label="Max Tokens" type="number" value={config.llm.max_tokens} onChange={(v) => handleChange('llm', 'max_tokens', parseInt(v))} />
                    </div>
                </Section>

                {/* Voice Section */}
                <Section title="Voice Synthesis (TTS)" icon={<Mic size={20} />}>
                    <Field label="ElevenLabs Voice ID" value={config.voice.voice_id} onChange={(v) => handleChange('voice', 'voice_id', v)} />

                    <div className="space-y-4 pt-2">
                        <RangeField label="Stability" value={config.voice.stability} onChange={(v) => handleChange('voice', 'stability', parseFloat(v))} />
                        <RangeField label="Similarity Boost" value={config.voice.similarity_boost} onChange={(v) => handleChange('voice', 'similarity_boost', parseFloat(v))} />
                        <RangeField label="Style Exaggeration" value={config.voice.style} onChange={(v) => handleChange('voice', 'style', parseFloat(v))} />
                    </div>
                </Section>

                {/* Prompts Section (Full Width) */}
                <div className="lg:col-span-2 bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm">
                    <h3 className="text-lg font-semibold mb-4 text-primary flex items-center gap-2">
                        <Shield size={20} /> System Persona & Rules
                    </h3>
                    <label className="block text-sm font-medium text-slate-400 mb-2">Core System Instruction</label>
                    <textarea
                        className="w-full h-96 bg-slate-900 border border-slate-700 rounded-lg p-4 font-mono text-sm text-slate-300 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary leading-relaxed"
                        value={config.prompts.system_prompt}
                        onChange={(e) => handleChange('prompts', 'system_prompt', e.target.value)}
                    />
                </div>
            </div>
        </div>
    );
}

const Section = ({ title, icon, children }) => (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-sm">
        <h3 className="text-lg font-semibold mb-6 text-primary flex items-center gap-2">
            {icon} {title}
        </h3>
        <div className="space-y-5">{children}</div>
    </div>
);

const Field = ({ label, value, onChange, type = "text", ...props }) => (
    <div>
        <label className="block text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wider">{label}</label>
        <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            {...props}
        />
    </div>
);

const RangeField = ({ label, value, onChange }) => (
    <div>
        <div className="flex justify-between mb-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</label>
            <span className="text-xs text-primary font-mono">{value}</span>
        </div>
        <input
            type="range" step="0.05" min="0" max="1"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
        />
    </div>
);
