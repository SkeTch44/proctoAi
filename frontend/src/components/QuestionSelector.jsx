import React, { useState, useEffect } from "react";

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

const QUESTION_TYPES = {
    mcq: { label: 'MCQ', color: 'blue' },
    short_answer: { label: 'Short', color: 'green' },
    essay: { label: 'Essay', color: 'purple' },
    true_false: { label: 'T/F', color: 'yellow' },
    fill_blanks: { label: 'Fill', color: 'orange' }
};

const DIFFICULTY_COLORS = {
    easy: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    hard: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    expert: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
};

export default function QuestionSelector({ selectedIds, onSelectionChange }) {
    const [questions, setQuestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [topic, setTopic] = useState('');
    const [type, setType] = useState('');
    const [difficulty, setDifficulty] = useState('');
    const [totalCount, setTotalCount] = useState(0);
    const [selectingAll, setSelectingAll] = useState(false);

    const fetchQuestions = React.useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: '20', // Increased for better picker EXPERIENCE
                topic: topic,
                type: type,
                difficulty: difficulty
            });

            const response = await fetch(`${API_BASE}/api/questions?${params}`, {
                headers: getAuthHeader()
            });

            if (!response.ok) throw new Error('Failed to fetch questions');

            const data = await response.json();
            setQuestions(data.questions || []);
            setTotalPages(data.pagination?.total_pages || 1);
            setTotalCount(data.pagination?.total_count || 0);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [page, topic, type, difficulty]);

    useEffect(() => {
        fetchQuestions();
    }, [fetchQuestions]);

    const toggleQuestion = (id) => {
        if (selectedIds.includes(id)) {
            onSelectionChange(selectedIds.filter(i => i !== id));
        } else {
            onSelectionChange([...selectedIds, id]);
        }
    };

    const isAllPageSelected = questions.length > 0 && questions.every(q => selectedIds.includes(q.id));

    const handleSelectAll = (e) => {
        if (e.target.checked) {
            const newSelected = [...selectedIds];
            questions.forEach(q => {
                if (!newSelected.includes(q.id)) {
                    newSelected.push(q.id);
                }
            });
            onSelectionChange(newSelected);
        } else {
            const currentIds = questions.map(q => q.id);
            onSelectionChange(selectedIds.filter(id => !currentIds.includes(id)));
        }
    };

    const selectAllMatching = async () => {
        setSelectingAll(true);
        try {
            const params = new URLSearchParams({
                topic: topic,
                type: type,
                difficulty: difficulty
            });
            const res = await fetch(`${API_BASE}/api/questions/ids?${params}`, {
                headers: getAuthHeader()
            });
            const data = await res.json();
            if (data.ids) {
                // Combine with existing selections from other searches
                const combined = Array.from(new Set([...selectedIds, ...data.ids]));
                onSelectionChange(combined);
            }
        } catch (err) {
            console.error("Select All failed", err);
        } finally {
            setSelectingAll(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                    type="text"
                    placeholder="Search Topic..."
                    value={topic}
                    onChange={(e) => {setTopic(e.target.value); setPage(1);}}
                    className="px-3 py-2 rounded-lg border dark:border-gray-700 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
                <select
                    value={type}
                    onChange={(e) => {setType(e.target.value); setPage(1);}}
                    className="px-3 py-2 rounded-lg border dark:border-gray-700 dark:bg-gray-800 text-sm"
                >
                    <option value="">All Types</option>
                    <option value="mcq">MCQ</option>
                    <option value="short_answer">Short Answer</option>
                    <option value="essay">Essay</option>
                </select>
                <select
                    value={difficulty}
                    onChange={(e) => {setDifficulty(e.target.value); setPage(1);}}
                    className="px-3 py-2 rounded-lg border dark:border-gray-700 dark:bg-gray-800 text-sm"
                >
                    <option value="">All Difficulties</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                    <option value="expert">Expert</option>
                </select>
            </div>

            {/* Select All Banner (Gmail Style) */}
            {isAllPageSelected && totalCount > questions.length && (
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-center text-xs">
                    {questions.every(q => selectedIds.includes(q.id)) && questions.length > 0 && totalCount > selectedIds.filter(id => questions.some(q => q.id === id) || !questions.some(q => q.id === id)).length ? (
                         <>
                            <span className="text-gray-700 dark:text-gray-300">
                                All {questions.length} questions on this page are selected. 
                            </span>
                            <button 
                                onClick={selectAllMatching} 
                                disabled={selectingAll}
                                className="ml-2 font-bold text-blue-600 dark:text-blue-400 hover:underline"
                            >
                                {selectingAll ? "Selecting..." : `Select all ${totalCount} matching questions`}
                            </button>
                         </>
                    ) : (
                        <span className="text-gray-700 dark:text-gray-300 font-medium">
                            🎉 All {totalCount} questions matching this filter are selected.
                        </span>
                    )}
                </div>
            )}

            <div className="border dark:border-gray-700 rounded-xl overflow-hidden bg-white dark:bg-gray-800/50">
                <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                            <th className="p-3 w-10 text-center">
                                <input 
                                    type="checkbox"
                                    checked={isAllPageSelected}
                                    onChange={handleSelectAll}
                                    className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 cursor-pointer"
                                    title="Select all on this page"
                                />
                            </th>
                            <th className="p-3">Question Text</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Difficulty</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y dark:divide-gray-700">
                        {loading ? (
                            <tr><td colSpan="4" className="p-10 text-center">Loading...</td></tr>
                        ) : questions.length === 0 ? (
                            <tr><td colSpan="4" className="p-10 text-center text-gray-500">No questions found</td></tr>
                        ) : (
                            questions.map(q => (
                                <tr key={q.id} className="hover:bg-gray-100 dark:hover:bg-gray-700/50 transition">
                                    <td className="p-3">
                                        <input
                                            type="checkbox"
                                            checked={selectedIds.includes(q.id)}
                                            onChange={() => toggleQuestion(q.id)}
                                            className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600"
                                        />
                                    </td>
                                    <td className="p-3 font-medium text-gray-800 dark:text-gray-200">
                                        {q.question_text.substring(0, 100)}...
                                    </td>
                                    <td className="p-3">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium bg-${QUESTION_TYPES[q.question_type]?.color || 'gray'}-100 text-${QUESTION_TYPES[q.question_type]?.color || 'gray'}-800`}>
                                            {QUESTION_TYPES[q.question_type]?.label || q.question_type}
                                        </span>
                                    </td>
                                    <td className="p-3">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${DIFFICULTY_COLORS[q.difficulty] || ''}`}>
                                            {q.difficulty}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="flex justify-between items-center px-2">
                <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
                <div className="flex gap-2">
                    <button 
                        onClick={() => setPage(p => Math.max(1, p - 1))} 
                        disabled={page === 1}
                        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded disabled:opacity-50"
                    >
                        Prev
                    </button>
                    <button 
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))} 
                        disabled={page === totalPages}
                        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
}
