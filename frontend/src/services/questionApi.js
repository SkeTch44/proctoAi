// Question Generation API Service
// Handles all 3 generation modes: Pure AI, RAG+LLM, PDF Scan

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

/**
 * Mode 1: Generate questions using pure AI (topic only)
 * Uses async Universal Engine with job polling
 */
export const generateQuestionsAI = async (params) => {
    const { topic, count, difficulty, types, bankId } = params;

    // Step 1: Dispatch async job
    const response = await fetch(`${API_BASE}/api/generate_questions_universal`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader()
        },
        body: JSON.stringify({
            subject: topic,
            total_questions: count || 10,
            difficulty: difficulty || 'medium',
            format: { [types[0]]: count || 10 },
            bank_id: bankId
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to start question generation');
    }

    const { job_id } = await response.json();

    // Step 2: Poll for completion (max 3 minutes, check every 2 seconds)
    for (let i = 0; i < 90; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));

        const statusResponse = await fetch(`${API_BASE}/api/generation_status/${job_id}`, {
            headers: getAuthHeader()
        });

        if (!statusResponse.ok) {
            throw new Error('Failed to check generation status');
        }

        const status = await statusResponse.json();

        if (status.state === 'completed') {
            return {
                questions: status.result.questions || [],
                count: status.result.count || 0,
                message: 'Questions generated successfully'
            };
        } else if (status.state === 'failed') {
            throw new Error(status.result?.message || 'Generation failed');
        }
        // Continue polling if still processing
    }

    throw new Error('Generation timed out after 3 minutes. Please try again with fewer questions.');
};

/**
 * Mode 2: Generate questions from uploaded document using RAG
 */
export const generateQuestionsRAG = async (file, params) => {
    const { topic, count, difficulty, types, bankId } = params;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('topic', topic || 'Document Content');
    formData.append('count', count || 10);
    formData.append('difficulty', difficulty || 'medium');
    if (types && types.length > 0) {
        types.forEach(t => formData.append('types', t));
    }
    if (bankId) {
        formData.append('bank_id', bankId);
    }

    const response = await fetch(`${API_BASE}/api/questions/generate/rag`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: formData
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to generate questions from document');
    }

    return response.json();
};

/**
 * Mode 3: Scan existing question PDF and extract questions
 */
export const scanQuestionsPDF = async (file, params) => {
    const { topic, bankId } = params;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('topic', topic || 'Extracted Questions');
    if (bankId) {
        formData.append('bank_id', bankId);
    }

    const response = await fetch(`${API_BASE}/api/questions/scan`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: formData
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to scan questions from PDF');
    }

    return response.json();
};

export default {
    generateQuestionsAI,
    generateQuestionsRAG,
    scanQuestionsPDF
};
