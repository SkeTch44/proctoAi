import { getToken } from "../../utils/authStorage";
import { API_BASE, getAuthHeader } from "../../utils/apiConfig";

export default function Support() {
  const [activeCategory, setActiveCategory] = useState("faq");
  const [searchQuery, setSearchQuery] = useState("");
  const [tickets, setTickets] = useState([]);
  const [ticketForm, setTicketForm] = useState({
    type: "general",
    subject: "",
    message: ""
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState("");

  // Fetch user tickets
  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/support/tickets`, {
        headers: getAuthHeader()
      });
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch (e) {
      console.error("Failed to fetch tickets:", e);
    }
  };

  const handleSubmitTicket = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitStatus("");

    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/support/tickets`, {
        method: "POST",
        headers: {
          ...getAuthHeader(),
          "Content-Type": "application/json"
        },
        body: JSON.stringify(ticketForm)
      });

      if (res.ok) {
        setSubmitStatus("✅ Ticket submitted successfully! We'll respond within 24 hours.");
        setTicketForm({ type: "general", subject: "", message: "" });
        fetchTickets(); // Refresh tickets list
        setTimeout(() => setSubmitStatus(""), 5000);
      } else {
        setSubmitStatus("❌ Failed to submit ticket. Please try again.");
      }
    } catch (e) {
      setSubmitStatus("❌ Network error. Please check your connection.");
    } finally {
      setSubmitting(false);
    }
  };

  // Static FAQ
  const faqCategories = {
    faq: { title: "Frequently Asked Questions", articles: [/* ... same FAQ data ... */] },
    technical: { title: "Technical Issues", articles: [/* ... */] },
    policy: { title: "Exam Policies", articles: [/* ... */] }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl mx-auto mb-6 shadow-2xl flex items-center justify-center">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h1 className="text-4xl font-black bg-gradient-to-r from-gray-900 via-blue-900 to-purple-900 bg-clip-text text-transparent dark:from-blue-400 dark:via-purple-400 dark:to-pink-400 mb-3">
          Help & Support
        </h1>
      </div>

      {/* Submit Report Form */}
      <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-2xl border border-orange-200/50 p-8 mb-8 shadow-xl">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3">
          📝 Submit Support Request
        </h2>

        {submitStatus && (
          <div className={`p-4 rounded-xl mb-6 text-sm font-semibold ${submitStatus.includes("✅")
              ? "bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 text-green-700 dark:text-green-200"
              : "bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-200"
            }`}>
            {submitStatus}
          </div>
        )}

        <form onSubmit={handleSubmitTicket} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Issue Type *
            </label>
            <select
              value={ticketForm.type}
              onChange={(e) => setTicketForm({ ...ticketForm, type: e.target.value })}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold"
              required
            >
              <option value="technical">Technical Issue</option>
              <option value="policy">Exam Policy</option>
              <option value="general">General Support</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Subject *
            </label>
            <input
              type="text"
              value={ticketForm.subject}
              onChange={(e) => setTicketForm({ ...ticketForm, subject: e.target.value })}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold"
              placeholder="e.g. Camera not working"
              required
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Description *
            </label>
            <textarea
              rows={4}
              value={ticketForm.message}
              onChange={(e) => setTicketForm({ ...ticketForm, message: e.target.value })}
              className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-semibold resize-vertical"
              placeholder="Describe your issue in detail..."
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting || !ticketForm.subject || !ticketForm.message}
            className="md:col-span-2 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white py-4 px-8 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Submitting..." : "Submit Support Request"}
          </button>
        </form>
      </div>

      {/* Recent Tickets */}
      {tickets.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border p-6 mb-8">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Your Recent Tickets ({tickets.length})
          </h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {tickets.slice(0, 5).map((ticket) => (
              <div key={ticket.id} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl border-l-4 border-blue-500">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-gray-900 dark:text-white">{ticket.subject}</h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${ticket.status === 'open' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-200' :
                      ticket.status === 'resolved' ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }`}>
                    {ticket.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2 line-clamp-2">
                  {ticket.message}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {new Date(ticket.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            icon: "📧",
            title: "Email Support",
            description: "Detailed assistance",
            onClick: () => window.location.href = "mailto:support@examplatform.com"
          },
          {
            icon: "📱",
            title: "Call Support",
            description: "Phone assistance",
            onClick: () => window.open("tel:+911234567890")
          }
        ].map((action, idx) => (
          <button
            key={idx}
            onClick={action.onClick}
            className="group w-full p-6 bg-gradient-to-r from-emerald-50 to-blue-50 dark:from-emerald-900/20 dark:to-blue-900/20 rounded-2xl border border-emerald-200/50 shadow-sm hover:shadow-xl hover:-translate-y-2 transition-all cursor-pointer h-full flex flex-col items-center text-center"
          >
            <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">{action.icon}</div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 group-hover:text-emerald-600">
              {action.title}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 flex-1">
              {action.description}
            </p>
            <span className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-blue-600 text-white rounded-xl font-semibold text-sm shadow-lg hover:shadow-xl transition-all">
              Connect Now
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
