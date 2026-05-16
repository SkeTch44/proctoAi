// src/pages/student/Feedback.jsx
import { getToken } from "../../utils/authStorage";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function Feedback() {
  const [feedbackForm, setFeedbackForm] = useState({
    rating: 5,
    category: "general",
    subject: "",
    message: "",
    suggestions: ""
  });
  const [userFeedback, setUserFeedback] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState("");

  // Rating hover state
  const [hoverRating, setHoverRating] = useState(0);

  // Fetch user feedback history
  useEffect(() => {
    fetchFeedback();
  }, []);

  const fetchFeedback = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/feedback`, {
        headers: getAuthHeader()
      });
      if (res.ok) {
        const data = await res.json();
        setUserFeedback(data.feedback || []);
      }
    } catch (e) {
      console.error("Failed to fetch feedback:", e);
    }
  };

  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    if (!feedbackForm.subject.trim() || !feedbackForm.message.trim()) {
      setSubmitStatus("❌ Please fill subject and message");
      return;
    }

    setSubmitting(true);
    setSubmitStatus("");

    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: {
          ...getAuthHeader(),
          "Content-Type": "application/json"
        },
        body: JSON.stringify(feedbackForm)
      });

      if (res.ok) {
        const data = await res.json();
        setSubmitStatus("✅ Thank you! Your feedback has been submitted.");
        setFeedbackForm({ rating: 5, category: "general", subject: "", message: "", suggestions: "" });
        fetchFeedback(); // Refresh history
        setTimeout(() => setSubmitStatus(""), 5000);
      } else {
        setSubmitStatus("❌ Failed to submit. Please try again.");
      }
    } catch (e) {
      setSubmitStatus("❌ Network error. Please check connection.");
    } finally {
      setSubmitting(false);
    }
  };

  const categories = [
    { value: "general", label: "General Experience" },
    { value: "exams", label: "Exam Process" },
    { value: "proctoring", label: "Proctoring" },
    { value: "ui", label: "User Interface" },
    { value: "performance", label: "Performance" },
    { value: "other", label: "Other" }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="w-20 h-20 bg-gradient-to-r from-emerald-500 to-blue-600 rounded-3xl mx-auto mb-6 shadow-2xl flex items-center justify-center">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
        </div>
        <h1 className="text-4xl font-black bg-gradient-to-r from-gray-900 via-emerald-900 to-blue-900 bg-clip-text text-transparent dark:from-emerald-400 dark:via-blue-400 dark:to-purple-400 mb-3">
          Your Feedback Matters
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          Help us improve the platform. Your input shapes our future.
        </p>
      </div>

      {/* Feedback Form */}
      <div className="bg-gradient-to-br from-emerald-50 via-blue-50 to-purple-50 dark:from-gray-800/50 dark:to-blue-900/10 rounded-3xl border border-emerald-200/50 shadow-2xl p-8 mb-12">
        <form onSubmit={handleSubmitFeedback} className="space-y-8">
          {/* Rating Stars */}
          <div className="text-center">
            <div className="flex justify-center mb-4">
              {[5, 4, 3, 2, 1].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setFeedbackForm({...feedbackForm, rating: star})}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className={`text-4xl transition-all ${
                    star <= (hoverRating || feedbackForm.rating)
                      ? "text-yellow-400 fill-current"
                      : "text-gray-300"
                  } hover:text-yellow-400 mx-1 transform hover:scale-110`}
                >
                  ⭐
                </button>
              ))}
            </div>
            <p className={`text-sm font-semibold transition-all ${
              feedbackForm.rating >= 4 ? "text-emerald-600 dark:text-emerald-400" :
              feedbackForm.rating === 3 ? "text-amber-600 dark:text-amber-400" :
              feedbackForm.rating <= 2 ? "text-red-600 dark:text-red-400" : "text-gray-600"
            }`}>
              Rating: {feedbackForm.rating}/5 {feedbackForm.rating >= 4 ? "Excellent!" : feedbackForm.rating === 3 ? "Good" : "Needs Improvement"}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">
                Category *
              </label>
              <select
                value={feedbackForm.category}
                onChange={(e) => setFeedbackForm({...feedbackForm, category: e.target.value})}
                className="w-full px-5 py-4 border-2 border-gray-200 dark:border-gray-600 rounded-2xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 bg-white dark:bg-gray-700 text-lg font-semibold shadow-sm transition-all"
                required
              >
                {categories.map(cat => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">
                Subject *
              </label>
              <input
                type="text"
                value={feedbackForm.subject}
                onChange={(e) => setFeedbackForm({...feedbackForm, subject: e.target.value})}
                className="w-full px-5 py-4 border-2 border-gray-200 dark:border-gray-600 rounded-2xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 bg-white dark:bg-gray-700 text-lg font-semibold shadow-sm transition-all"
                placeholder="What would you like to share?"
                maxLength={100}
                required
              />
              <p className="text-xs text-gray-500 mt-1">{feedbackForm.subject.length}/100</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">
              Your Feedback * (2000 chars max)
            </label>
            <textarea
              rows={6}
              value={feedbackForm.message}
              onChange={(e) => setFeedbackForm({...feedbackForm, message: e.target.value})}
              className="w-full px-5 py-4 border-2 border-gray-200 dark:border-gray-600 rounded-2xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 bg-white dark:bg-gray-700 text-lg font-semibold shadow-sm transition-all resize-vertical"
              placeholder="Tell us about your experience. What worked well? What can be improved?"
              maxLength={2000}
              required
            />
            <p className="text-xs text-gray-500 mt-1">{feedbackForm.message.length}/2000</p>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 dark:text-gray-200 mb-3">
              Suggestions (Optional)
            </label>
            <textarea
              rows={3}
              value={feedbackForm.suggestions}
              onChange={(e) => setFeedbackForm({...feedbackForm, suggestions: e.target.value})}
              className="w-full px-5 py-4 border border-gray-200 dark:border-gray-600 rounded-2xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 bg-gray-50 dark:bg-gray-700/50 text-lg transition-all"
              placeholder="Any specific features or improvements you'd like to see?"
              maxLength={1000}
            />
          </div>

          {submitStatus && (
            <div className={`p-6 rounded-2xl text-lg font-semibold text-center border-4 ${
              submitStatus.includes("✅") 
                ? "bg-emerald-100 dark:bg-emerald-900/30 border-emerald-400 dark:border-emerald-500 text-emerald-800 dark:text-emerald-200"
                : "bg-red-100 dark:bg-red-900/30 border-red-400 dark:border-red-500 text-red-800 dark:text-red-200"
            }`}>
              {submitStatus}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !feedbackForm.subject.trim() || !feedbackForm.message.trim()}
            className="w-full bg-gradient-to-r from-emerald-500 via-emerald-600 to-blue-600 hover:from-emerald-600 hover:via-emerald-700 hover:to-blue-700 text-white py-6 px-8 rounded-3xl font-black text-xl shadow-2xl hover:shadow-3xl transform hover:-translate-y-1 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {submitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-7 w-7 text-white inline" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Submitting Feedback...
              </>
            ) : (
              "Submit Feedback →"
            )}
          </button>
        </form>
      </div>

      {/* Feedback History */}
      {userFeedback.length > 0 && (
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-3xl border border-emerald-200/50 shadow-2xl p-8">
          <h2 className="text-2xl font-black text-gray-900 dark:text-white mb-6 flex items-center gap-3">
            📋 Your Feedback History ({userFeedback.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-h-96 overflow-y-auto">
            {userFeedback.slice(0, 6).map((fb) => (
              <div key={fb.id} className="p-6 bg-gradient-to-r from-gray-50 to-emerald-50 dark:from-gray-800/50 dark:to-emerald-900/20 rounded-2xl border border-gray-200/50 shadow-sm hover:shadow-xl transition-all">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-bold text-lg text-gray-900 dark:text-white flex-1 pr-3 line-clamp-1">
                    {fb.subject}
                  </h3>
                  <div className="flex gap-1">
                    {[...Array(5)].map((_, i) => (
                      <span key={i} className={`text-lg ${
                        i < fb.rating ? "text-yellow-400 fill-current" : "text-gray-300"
                      }`}>
                        ⭐
                      </span>
                    ))}
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-3">
                  {fb.message}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>{new Date(fb.created_at).toLocaleDateString()}</span>
                  <span className="font-semibold capitalize">{fb.category}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
