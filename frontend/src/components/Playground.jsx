import React, { useState, useRef, useEffect } from 'react';
import { chat } from '../lib/api';
import { Send, User, Bot, Loader2 } from 'lucide-react';

export default function Playground() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Namaste! Main Aditi, TMU se. Kaise madad kar sakti hoon aapki?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await chat(input);
            // API returns: { response: "...", ... }
            setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'error', content: 'Error: ' + err.message }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-140px)] max-w-4xl mx-auto p-4">
            <div className="bg-slate-800 rounded-t-xl p-4 border-b border-slate-700 flex justify-between items-center">
                <h2 className="text-lg font-bold text-white flex items-center gap-2"><Bot className="text-primary" /> Test Playground</h2>
                <span className="text-xs bg-primary/20 text-primary px-2 py-1 rounded">Live Configuration</span>
            </div>

            <div className="flex-1 bg-slate-900 overflow-y-auto p-4 space-y-4 border-x border-slate-800" ref={scrollRef}>
                {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`flex gap-3 max-w-[80%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === 'user' ? 'bg-slate-700' : 'bg-primary'}`}>
                                {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>
                            <div className={`p-3 rounded-lg text-sm leading-relaxed ${m.role === 'user' ? 'bg-slate-800 text-slate-200' :
                                    m.role === 'error' ? 'bg-red-900/50 text-red-200' :
                                        'bg-slate-800/50 text-slate-100 border border-slate-700'
                                }`}>
                                {m.content}
                            </div>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="flex gap-3 max-w-[80%]">
                            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                                <Loader2 size={16} className="animate-spin" />
                            </div>
                            <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg text-sm text-slate-400">
                                Aditi is thinking...
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <form onSubmit={handleSend} className="bg-slate-800 p-4 rounded-b-xl border-t border-slate-700 flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type a message to test the agent..."
                    className="flex-1 bg-slate-900 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-primary border border-slate-700"
                />
                <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="bg-primary hover:bg-orange-600 text-white px-6 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    <Send size={20} />
                </button>
            </form>
        </div>
    );
}
