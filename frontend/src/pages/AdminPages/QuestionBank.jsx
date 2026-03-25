// src/pages/AdminPages/QuestionBank.jsx
// View and manage saved questions from all generation modes

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
    easy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    hard: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    expert: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
};

export default function QuestionBank() {
    const [questions, setQuestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [filters, setFilters] = useState({
        topic: '',
        type: '',
        difficulty: ''
    });

    // Selection State
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [selectedQuestion, setSelectedQuestion] = useState(null);

    // Exam Creation State
    const [showExamModal, setShowExamModal] = useState(false);
    const [examTitle, setExamTitle] = useState("");
    const [examDuration, setExamDuration] = useState(60);
    const [creatingExam, setCreatingExam] = useState(false);

    useEffect(() => {
        fetchQuestions();
    }, [page, filters]);

    const fetchQuestions = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: '20',
                ...Object.fromEntries(
                    Object.entries(filters).filter(([_, v]) => v !== '')
                )
            });

            const response = await fetch(`${API_BASE}/api/question-bank/questions?${params}`, {
                headers: getAuthHeader()
            });

            if (!response.ok) throw new Error('Failed to fetch questions');

            const data = await response.json();
            setQuestions(data.questions || []);
            setTotalPages(data.pages || 1);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
        setPage(1);
    };

    // Selection Handlers
    const toggleSelectAll = () => {
        if (selectedIds.size === questions.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(questions.map(q => q.id)));
        }
    };

    const toggleSelect = (id) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    };

    // Exam Creation Logic
    const handleCreateExam = async () => {
        if (!examTitle.trim()) {
            alert('Please enter an exam title');
            return;
        }

        setCreatingExam(true);
        try {
            const token = localStorage.getItem('token');
            const selectedQuestionsList = questions.filter(q => selectedIds.has(q.id));

            const payload = {
                title: examTitle,
                description: `Created from Question Bank (${selectedQuestionsList.length} questions)`,
                questions: selectedQuestionsList, // Send objects directly
                duration: parseInt(examDuration)
            };

            console.log("🚀 Creating exam from bank:", payload);

            const response = await fetch(`${API_BASE}/api/exams`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Failed to create exam: ${errText}`);
            }

            const data = await response.json();
            alert(`✅ Exam "${examTitle}" created successfully!`);

            // Reset selection and modal
            setShowExamModal(false);
            setSelectedIds(new Set());
            setExamTitle("");
        } catch (err) {
            console.error(err);
            alert(`❌ Error creating exam: ${err.message}`);
        } finally {
            setCreatingExam(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                        📚 Question Bank
                    </h2>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Select questions to create a new exam
                    </p>
                </div>
                <div className="flex gap-3">
                    {selectedIds.size > 0 && (
                        <button
                            onClick={() => setShowExamModal(true)}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium shadow-sm flex items-center gap-2"
                        >
                            📝 Create Exam ({selectedIds.size})
                        </button>
                    )}
                    <a
                        href="/admin/questions/generate"
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
                    >
                        + Generate New
                    </a>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-4 mb-6 shadow border border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-4 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Search Topic
                        </label>
                        <input
                            type="text"
                            value={filters.topic}
                            onChange={(e) => handleFilterChange('topic', e.target.value)}
                            placeholder="e.g. Machine Learning"
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 
                         bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Type
                        </label>
                        <select
                            value={filters.type}
                            onChange={(e) => handleFilterChange('type', e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 
                         bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        >
                            <option value="">All Types</option>
                            <option value="mcq">MCQ</option>
                            <option value="short_answer">Short Answer</option>
                            <option value="essay">Essay</option>
                            <option value="true_false">True/False</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Difficulty
                        </label>
                        <select
                            value={filters.difficulty}
                            onChange={(e) => handleFilterChange('difficulty', e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 
                         bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        >
                            <option value="">All Levels</option>
                            <option value="easy">Easy</option>
                            <option value="medium">Medium</option>
                            <option value="hard">Hard</option>
                            <option value="expert">Expert</option>
                        </select>
                    </div>

                    <div className="flex items-end">
                        <button
                            onClick={() => setFilters({ topic: '', type: '', difficulty: '' })}
                            className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 
                         dark:hover:bg-gray-700 rounded-lg transition"
                        >
                            Clear Filters
                        </button>
                    </div>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 p-4 rounded-lg mb-4">
                    ⚠️ {error}
                </div>
            )}

            {/* Loading */}
            {loading ? (
                <div className="text-center py-12">
                    <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
                    <p className="mt-2 text-gray-500">Loading questions...</p>
                </div>
            ) : (
                <>
                    {/* Questions Table */}
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <table className="w-full">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                                <tr>
                                    <th className="px-4 py-3 text-left">
                                        <input
                                            type="checkbox"
                                            checked={questions.length > 0 && selectedIds.size === questions.length}
                                            onChange={toggleSelectAll}
                                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        />
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Question
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Topic
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Type
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Difficulty
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Points
                                    </th>
                                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                {questions.length === 0 ? (
                                    <tr>
                                        <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                                            No questions found. Try adjusting filters or generate new questions.
                                        </td>
                                    </tr>
                                ) : (
                                    questions.map((q) => (
                                        <tr
                                            key={q.id}
                                            className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition cursor-pointer ${selectedIds.has(q.id) ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                                }`}
                                            onClick={() => toggleSelect(q.id)}
                                        >
                                            <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedIds.has(q.id)}
                                                    onChange={() => toggleSelect(q.id)}
                                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                />
                                            </td>
                                            <td className="px-4 py-3">
                                                <p className="text-gray-900 dark:text-gray-100 font-medium truncate max-w-md">
                                                    {q.question_text?.substring(0, 80)}...
                                                </p>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                                    {q.topic || '-'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`px-2 py-1 rounded-full text-xs font-medium 
                          ${QUESTION_TYPES[q.question_type]?.color === 'blue' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' : ''}
                          ${QUESTION_TYPES[q.question_type]?.color === 'green' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : ''}
                          ${QUESTION_TYPES[q.question_type]?.color === 'purple' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' : ''}`}>
                                                    {QUESTION_TYPES[q.question_type]?.label || q.question_type}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${DIFFICULTY_COLORS[q.difficulty] || ''}`}>
                                                    {q.difficulty || '-'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                                                {q.points || 1}
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setSelectedQuestion(q);
                                                    }}
                                                    className="text-blue-600 hover:text-blue-800 dark:text-blue-400 text-sm"
                                                >
                                                    View
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    <div className="flex justify-between items-center mt-4">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                            Page {page} of {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-3 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 
                           disabled:opacity-50 hover:bg-gray-200 dark:hover:bg-gray-600 transition"
                            >
                                ← Prev
                            </button>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="px-3 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 
                           disabled:opacity-50 hover:bg-gray-200 dark:hover:bg-gray-600 transition"
                            >
                                Next →
                            </button>
                        </div>
                    </div>
                </>
            )}

            {/* Question Detail Modal */}
            {selectedQuestion && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedQuestion(null)}>
                    <div
                        className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-2xl w-full m-4 max-h-[80vh] overflow-y-auto shadow-2xl"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Modal content same as before */}
                        <div className="flex justify-between items-start mb-4">
                            <div className="flex gap-2">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium 
                  ${QUESTION_TYPES[selectedQuestion.question_type]?.color === 'blue' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                                    {QUESTION_TYPES[selectedQuestion.question_type]?.label || selectedQuestion.question_type}
                                </span>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${DIFFICULTY_COLORS[selectedQuestion.difficulty] || ''}`}>
                                    {selectedQuestion.difficulty}
                                </span>
                            </div>
                            <button
                                onClick={() => setSelectedQuestion(null)}
                                className="text-gray-400 hover:text-gray-600 text-2xl"
                            >
                                ×
                            </button>
                        </div>

                        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                            {selectedQuestion.question_text}
                        </h3>

                        {selectedQuestion.question_type === 'mcq' && selectedQuestion.question_data?.options && (
                            <div className="space-y-2 mb-4">
                                {Object.entries(selectedQuestion.question_data.options).map(([key, value]) => (
                                    <div
                                        key={key}
                                        className={`p-3 rounded-lg border ${selectedQuestion.question_data.correct_answer === key
                                            ? 'border-green-500 bg-green-50 dark:bg-green-900/30'
                                            : 'border-gray-200 dark:border-gray-700'
                                            }`}
                                    >
                                        <span className="font-medium">{key})</span> {value}
                                        {selectedQuestion.question_data.correct_answer === key && (
                                            <span className="ml-2 text-green-600 text-sm">✓ Correct</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Create Exam Modal */}
            {showExamModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
                        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                            Create Exam
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Exam Title
                                </label>
                                <input
                                    type="text"
                                    value={examTitle}
                                    onChange={(e) => setExamTitle(e.target.value)}
                                    placeholder="e.g. Midterm Physics Exam"
                                    className="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Duration (minutes)
                                </label>
                                <input
                                    type="number"
                                    value={examDuration}
                                    onChange={(e) => setExamDuration(e.target.value)}
                                    className="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-sm text-blue-700 dark:text-blue-300">
                                <p>Selected Questions: <strong>{selectedIds.size}</strong></p>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end gap-3">
                            <button
                                onClick={() => setShowExamModal(false)}
                                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateExam}
                                disabled={creatingExam}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {creatingExam && (
                                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                )}
                                Create Exam
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
